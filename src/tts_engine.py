import io
import requests
import soundfile as sf
import yaml
from pathlib import Path
from src import config
from src.audio_utils import split_text_into_segments, crossfade_concat, humanize_audio
from src.text_preprocessor import preprocess_text


class TTSVoiceCloner:
    """HTTP-клиент для XTTS-v2 API сервера в Docker."""

    def __init__(self, config_path: str = "config.yaml"):
        # Загрузка конфигурации
        cfg_file = Path(config_path)
        if not cfg_file.exists():
            raise FileNotFoundError(f"Конфиг не найден: {config_path}")

        with open(cfg_file, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.api_url = self.cfg["tts"]["api_url"].rstrip("/")
        self._check_connection()
        self._apply_settings()

    def _check_connection(self):
        try:
            resp = requests.get(f"{self.api_url}/docs", timeout=5)
            if resp.status_code == 200:
                print(f"✅ XTTS API доступен: {self.api_url}")
            else:
                raise ConnectionError(f"API вернул статус {resp.status_code}")
        except requests.ConnectionError:
            raise ConnectionError(
                f"❌ Не удалось подключиться к XTTS API по адресу {self.api_url}. "
                "Убедитесь, что Docker-контейнер запущен (docker compose up -d)."
            )

    def _apply_settings(self):
        """Автоматически применяет настройки TTS при инициализации."""
        settings = self.cfg["tts"].get("default_settings", {})
        if settings:
            resp = requests.post(
                f"{self.api_url}/set_tts_settings",
                json=settings,
                timeout=5
            )
            if resp.status_code == 200:
                print(f"✅ Настройки TTS применены: speed={settings.get('speed')}, temp={settings.get('temperature')}")
            else:
                print(f"⚠️ Не удалось применить настройки: {resp.text}")

    def synthesize(self, reference_path: str, text: str, output_path: str) -> str:
        """
        Генерирует речь через XTTS-v2 API.
        Сегментация и склейка выполняются на клиенте.
        """
        ref_file = Path(reference_path)
        if not ref_file.exists():
            raise FileNotFoundError(f"Эталонный файл не найден: {reference_path}")

        # === ВОТ СЮДА ВСТАВЛЯЕШЬ ===
        text = preprocess_text(text)
        print(f"📝 Текст после предобработки:\n{text}\n{'='*50}")
        # ============================

        # Имя файла внутри контейнера (папка /app/example смонтирована)
        speaker_wav_name = ref_file.name

        max_len = self.cfg.get("audio", {}).get("max_segment_length", 250)
        segments = split_text_into_segments(text, max_len=max_len)
        if not segments:
            raise ValueError("Текст пустой после сегментации")

        audio_results = []
        for i, segment in enumerate(segments):
            print(f"Генерация сегмента {i + 1}/{len(segments)}...")

            response = requests.post(
                f"{self.api_url}/tts_to_audio/",
                json={
                    "text": segment,
                    "speaker_wav": speaker_wav_name,
                    "language": "ru",
                },
                timeout=120,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"API ошибка ({response.status_code}): {response.text}"
                )

            audio_np, sr = sf.read(
                io.BytesIO(response.content), dtype="float32"
            )
            audio_results.append(audio_np)

        sample_rate = self.cfg.get("audio", {}).get("sample_rate", config.AUDIO_SAMPLE_RATE)
        final_audio = crossfade_concat(audio_results, sr=sample_rate, fade_ms=50)
        final_audio = humanize_audio(final_audio, sample_rate)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, final_audio, sample_rate)

        print(f"✅ Аудио сохранено: {output_path}")
        return output_path