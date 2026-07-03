import gradio as gr
from pathlib import Path
from src.tts_engine import TTSVoiceCloner

# Инициализация движка (проверит Docker и применит настройки)
cloner = TTSVoiceCloner()

VOICES_DIR = Path("voices")
OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)


def get_available_voices():
    """Сканирует папку voices/ и возвращает список доступных эталонов."""
    if not VOICES_DIR.exists():
        return []
    return sorted([f.name for f in VOICES_DIR.iterdir() if f.suffix.lower() in {".wav", ".mp3", ".flac"}])


def synthesize_speech(voice_file: str, text: str, speed: float, temperature: float):
    """Основная функция синтеза для Gradio."""
    if not voice_file or not text.strip():
        raise gr.Error("Выберите голос и введите текст!")

    ref_path = VOICES_DIR / voice_file
    output_path = OUTPUTS_DIR / f"gradio_output_{Path(voice_file).stem}.wav"

    # Временно меняем настройки если они отличаются от дефолтных
    # (XTTS API сервер позволяет менять их на лету через set_tts_settings)
    import requests, yaml
    cfg_path = Path("config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    api_url = cfg["tts"]["api_url"].rstrip("/")
    requests.post(f"{api_url}/set_tts_settings", json={
        "speed": speed,
        "temperature": temperature,
        "top_p": 0.85,
        "repetition_penalty": 2.0
    }, timeout=5)

    result_path = cloner.synthesize(
        reference_path=str(ref_path),
        text=text,
        output_path=str(output_path)
    )

    return result_path


# === Интерфейс Gradio ===
with gr.Blocks(title="Voice Clone Studio") as demo:
    gr.Markdown("# 🎙️ Voice Clone Studio\nZero-Shot клонирование голоса на базе XTTS-v2")

    with gr.Row():
        with gr.Column(scale=1):
            voice_dropdown = gr.Dropdown(
                choices=get_available_voices(),
                label="Эталонный голос",
                info="Файлы из папки voices/"
            )
            refresh_btn = gr.Button("🔄 Обновить список голосов", size="sm")

            text_input = gr.Textbox(
                label="Текст для озвучки",
                placeholder="Введите текст здесь...",
                lines=6
            )

            with gr.Accordion("⚙️ Настройки синтеза", open=False):
                speed_slider = gr.Slider(minimum=0.5, maximum=1.5, value=0.9, step=0.05, label="Скорость")
                temp_slider = gr.Slider(minimum=0.3, maximum=1.0, value=0.7, step=0.05, label="Температура")

            synth_btn = gr.Button("🔊 Синтезировать речь", variant="primary", size="lg")

        with gr.Column(scale=1):
            audio_output = gr.Audio(label="Результат", type="filepath")
            gr.Markdown("---")
            gr.Markdown(
                "### 💡 Советы по качеству\n"
                "- **Эталонная запись:** используйте чистую разговорную речь без фона, музыки и эха\n"
                "- **Длительность:** 30–60 секунд достаточно для качественного клона\n"
                "- **Формат:** WAV PCM 24kHz Mono даёт лучший результат\n"
                "- **Стиль:** живая интонация (подкаст, интервью) работает лучше, чем дикторская читка\n"
                "- **Текст:** автоматически обрабатывается LLM для естественных пауз и ударений"
            )

    # Привязки событий
    refresh_btn.click(fn=get_available_voices, outputs=voice_dropdown)
    synth_btn.click(
        fn=synthesize_speech,
        inputs=[voice_dropdown, text_input, speed_slider, temp_slider],
        outputs=audio_output
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())