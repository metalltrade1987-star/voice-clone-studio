# src/chatterbox_engine.py
import torch
import soundfile as sf
import warnings
from pathlib import Path

# Игнорируем предупреждения о LoRA
warnings.filterwarnings("ignore", message=".*LoRACompatibleLinear.*")

# === ФИКС БАГА WATERMARKER (perth) ===
import sys


class FakePerth:
    class PerthImplicitWatermarker:
        def __call__(self, *args, **kwargs):
            return self

        def apply_watermark(self, wav, sample_rate=24000):
            return wav  # Прозрачная заглушка

        def embed(self, *args, **kwargs):
            pass

        def detect(self, *args, **kwargs):
            return False


sys.modules['perth'] = FakePerth()
# =====================================

# ИМПОРТ МУЛЬТИЯЗЫЧНОЙ МОДЕЛИ V3 (как в документации HF)
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from src.audio_utils import split_text_into_segments, crossfade_concat, humanize_audio
from src.text_preprocessor import preprocess_text


class ChatterboxVoiceCloner:
    """
    Локальный движок синтеза на базе Chatterbox Multilingual V3.
    Полностью совместим по интерфейсу с TTSVoiceCloner.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Chatterbox] Инициализация на {self.device.upper()}")

        try:
            # Убрали t3_model="v3", так как текущий pip-пакет его не поддерживает.
            # По умолчанию ChatterboxMultilingualTTS загружает актуальную мультиязычную модель.
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS

            self.model = ChatterboxMultilingualTTS.from_pretrained(
                device=self.device
            )
            print("✅ Модель Chatterbox Multilingual загружена успешно")

        except Exception as e:
            raise RuntimeError(
                f"❌ Не удалось загрузить Chatterbox: {e}\n"
                "Проверьте: pip install chatterbox-tts && torch>=2.6.0+cu124"
            )

        self.current_speed = 0.9
        self.current_temperature = 0.7

    def set_settings(self, speed: float = 0.9, temperature: float = 0.7, **kwargs):
        self.current_speed = speed
        self.current_temperature = temperature

    def synthesize(
            self,
            reference_path: str,
            text: str,
            output_path: str,
            language: str = "ru",
            sample_rate: int = 24000,
            speed: float = 0.9,
            temperature: float = 0.7
    ) -> str:
        """Синтез речи с клонированием голоса."""
        self.current_speed = speed
        self.current_temperature = temperature

        ref_file = Path(reference_path)
        if not ref_file.exists():
            raise FileNotFoundError(f"Эталонный файл не найден: {reference_path}")

        text = preprocess_text(text)

        max_len = 250
        segments = split_text_into_segments(text, max_len=max_len)
        if not segments:
            raise ValueError("Текст пустой после сегментации")

        audio_results = []
        model_sr = self.model.sr

        for i, segment in enumerate(segments):
            print(f"[Chatterbox] Генерация сегмента {i + 1}/{len(segments)}...")

            # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: language_id="ru"
            wav = self.model.generate(
                text=segment,
                audio_prompt_path=str(ref_file),
                language_id="ru",
                cfg_scale=0.0,  # <-- ОТКЛЮЧАЕТ НАСЛЕДОВАНИЕ АКЦЕНТА ЭТАЛОНА
                exaggeration=0.5  # <-- СТАНДАРТНАЯ ВЫРАЗИТЕЛЬНОСТЬ ДЛЯ РУССКОГО
            )

            wav_np = wav.squeeze(0).cpu().numpy()
            audio_results.append(wav_np)

        final_audio = crossfade_concat(audio_results, sr=model_sr, fade_ms=50)
        final_audio = humanize_audio(final_audio, model_sr)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, final_audio, model_sr)
        print(f"✅ [Chatterbox] Аудио сохранено: {output_path}")

        return output_path