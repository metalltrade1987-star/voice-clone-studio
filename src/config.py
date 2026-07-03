import os

# Настройки путей
VOICES_DIR = os.path.join(os.getcwd(), 'voices')
OUTPUTS_DIR = os.path.join(os.getcwd(), 'outputs')

# Параметры аудио
AUDIO_SAMPLE_RATE = 24000
AUDIO_BIT_DEPTH = 16
AUDIO_CHANNELS = 1

# Ограничения для RTX 3060
MAX_VRAM_USAGE = 8 * 1024 * 1024 * 1024  # 8GB в байтах
