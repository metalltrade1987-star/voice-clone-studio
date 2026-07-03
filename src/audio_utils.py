import re
import numpy as np
import librosa
import soundfile as sf
from src import config


def load_and_normalize(path: str) -> tuple[np.ndarray, int]:
    """Загрузка аудио с приведением к нужной частоте и нормализацией."""
    audio, sr = librosa.load(path, sr=config.AUDIO_SAMPLE_RATE)

    # Нормализация пиков до -1dBFS (0.89), чтобы избежать клиппинга при постпроцессинге
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio * (0.89 / peak)

    return audio, sr


def split_text_into_segments(text: str, max_len: int = 250) -> list[str]:
    """
    Сегментация текста с приоритетом на естественные паузы.
    Учитывает многоточия, тире и запятые, которые расставляет LLM.
    """
    if not text or not text.strip():
        return []

    # Приоритет разбивки: .!?... → ; → , → пробел
    # Разбиваем по предложениям и многоточиям
    raw_parts = re.split(r'(?<=[.!?…])\s+|(?<=—)\s+', text)

    segments = []
    current = ""

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue

        candidate = f"{current} {part}".strip() if current else part

        if len(candidate) <= max_len:
            current = candidate
        else:
            # Сохраняем накопленный сегмент
            if current:
                segments.append(current)

            # Если сама часть длиннее max_len, разбиваем по запятым
            if len(part) > max_len:
                sub_parts = re.split(r'(?<=,)\s+', part)
                current = ""
                for sp in sub_parts:
                    sp = sp.strip()
                    if not sp:
                        continue
                    c2 = f"{current} {sp}".strip() if current else sp
                    if len(c2) <= max_len:
                        current = c2
                    else:
                        if current:
                            segments.append(current)
                        current = sp
            else:
                current = part

    if current:
        segments.append(current)

    return segments


def crossfade_concat(audio_segments: list[np.ndarray], sr: int = 24000, fade_ms: int = 50) -> np.ndarray:
    """
    Умная склейка сегментов: ищет тихие точки на стыках для бесшовного перехода.
    Устраняет щелчки и артефакты на границах.
    """
    if not audio_segments:
        return np.array([], dtype=np.float32)
    if len(audio_segments) == 1:
        return audio_segments[0].copy()

    fade_samples = int(fade_ms * sr / 1000)
    search_window = min(int(0.15 * sr), fade_samples * 3)  # Ищем в окне до 150мс

    result = audio_segments[0].copy()

    for i in range(1, len(audio_segments)):
        seg = audio_segments[i]

        if len(seg) < fade_samples or len(result) < fade_samples:
            # Слишком короткий сегмент — просто конкатенируем
            result = np.concatenate([result, seg])
            continue

        # Находим самую тихую точку в конце текущего результата
        tail = result[-search_window:]
        quiet_tail_idx = np.argmin(np.abs(tail))
        cut_point = len(result) - search_window + quiet_tail_idx

        # Находим самую тихую точку в начале следующего сегмента
        head = seg[:search_window]
        quiet_head_idx = np.argmin(np.abs(head))
        seg_start = quiet_head_idx

        # Обрезаем до тихих точек
        result = result[:cut_point]
        seg = seg[seg_start:]

        # Применяем кроссфейд
        actual_fade = min(fade_samples, len(result), len(seg))
        if actual_fade > 0:
            fade_out = np.linspace(1.0, 0.0, actual_fade, dtype=np.float32)
            fade_in = np.linspace(0.0, 1.0, actual_fade, dtype=np.float32)

            overlap = result[-actual_fade:] * fade_out + seg[:actual_fade] * fade_in
            result = np.concatenate([result[:-actual_fade], overlap, seg[actual_fade:]])
        else:
            result = np.concatenate([result, seg])

    return result


def humanize_audio(audio: np.ndarray, sr: int) -> np.ndarray:
    """Финальная обработка: обрезка хвостов, удаление щелчков, мягкое затухание."""
    if len(audio) == 0:
        return audio

    # 1. Удаление щелчков: заменяем резкие пики интерполяцией
    threshold = 0.95
    clicks = np.where(np.abs(audio) > threshold)[0]
    for idx in clicks:
        if 1 <= idx < len(audio) - 1:
            audio[idx] = (audio[idx - 1] + audio[idx + 1]) / 2.0

    # 2. Обрезка тишины в конце
    silence_threshold = 0.005
    above = np.where(np.abs(audio) > silence_threshold)[0]
    if len(above) > 0:
        end_idx = min(above[-1] + int(0.15 * sr), len(audio))
        audio = audio[:end_idx]

    # 3. Мягкое затухание (fade out 40мс)
    fade_samples = int(0.04 * sr)
    if len(audio) > fade_samples:
        fade = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        audio[-fade_samples:] *= fade

    return audio