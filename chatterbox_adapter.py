# chatterbox_adapter.py
import torch
from pathlib import Path
from typing import Optional


class ChatterboxVoiceCloner:
    """
    Адаптер для Chatterbox-Turbo, совместимый с интерфейсом TTSVoiceCloner.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        # TODO: Загрузка модели Chatterbox
        print(f"[Chatterbox] Инициализация на {self.device}")

    def synthesize(
            self,
            reference_path: str,
            text: str,
            output_path: str,
            speed: float = 0.9,
            temperature: float = 0.7
    ) -> str:
        """
        Синтез речи с клонированием голоса.
        Интерфейс должен совпадать с TTSVoiceCloner.synthesize
        """
        ref_path = Path(reference_path)
        if not ref_path.exists():
            raise FileNotFoundError(f"Референсное аудио не найдено: {reference_path}")

        if self.model is None:
            raise RuntimeError("Модель Chatterbox не загружена")

        print(f"[Chatterbox] Генерация: '{text[:50]}...' | Speed={speed}, Temp={temperature}")

        # TODO: Реальный вызов Chatterbox с параметрами
        # result = self.model.generate(
        #     text=text,
        #     speaker_wav=str(ref_path),
        #     file_path=output_path,
        #     speed=speed,
        #     temperature=temperature
        # )

        # Временная заглушка
        import shutil
        shutil.copy(reference_path, output_path)
        print(f"[Chatterbox] Сохранено в {output_path}")

        return output_path

    def set_settings(self, speed: float, temperature: float, **kwargs):
        """
        Настройки применяются напрямую при синтезе,
        но метод нужен для совместимости с API.
        """
        # Chatterbox принимает параметры в generate(),
        # поэтому здесь можно просто сохранить их в self
        self.current_speed = speed
        self.current_temperature = temperature
        print(f"[Chatterbox] Настройки обновлены: speed={speed}, temp={temperature}")