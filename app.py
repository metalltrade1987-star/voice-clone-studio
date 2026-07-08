import gradio as gr
from pathlib import Path
from src.tts_engine import TTSVoiceCloner
from src.chatterbox_engine import ChatterboxVoiceCloner

# Инициализация папок
VOICES_DIR = Path("voices")
OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)


def get_available_voices():
    """Сканирует папку voices/ и возвращает список доступных эталонов."""
    if not VOICES_DIR.exists():
        return []
    return sorted([f.name for f in VOICES_DIR.iterdir() if f.suffix.lower() in {".wav", ".mp3", ".flac"}])


def synthesize_speech(engine_type: str, voice_file: str, text: str, speed: float, temperature: float):
    """Основная функция синтеза с выбором движка."""
    if not voice_file or not text.strip():
        raise gr.Error("Выберите голос и введите текст!")

    ref_path = VOICES_DIR / voice_file
    output_path = OUTPUTS_DIR / f"output_{Path(voice_file).stem}_{engine_type[:4]}.wav"

    # Выбор движка
    if engine_type == "Chatterbox (Local)":
        cloner = ChatterboxVoiceCloner()
        # У Chatterbox настройки передаются напрямую в метод
        result_path = cloner.synthesize(
            reference_path=str(ref_path),
            text=text,
            output_path=str(output_path),
            speed=speed,
            temperature=temperature
        )
    else:
        # XTTS через Docker API
        cloner = TTSVoiceCloner()
        # Для XTTS настройки применяются через отдельный вызов API внутри класса
        # Но так как мы создаем новый экземпляр каждый раз,
        # нужно убедиться, что _apply_settings() отработает или передать их иначе.
        # В текущей реализации TTSVoiceCloner применяет дефолтные из config.yaml.
        # Если нужны динамические настройки для XTTS - придется доработать tts_engine.py
        # Пока используем стандартный flow:
        result_path = cloner.synthesize(
            reference_path=str(ref_path),
            text=text,
            output_path=str(output_path)
        )

    return result_path


# === Интерфейс Gradio ===
with gr.Blocks(title="Voice Clone Studio | Dual Engine") as demo:
    gr.Markdown("# 🎙️ Voice Clone Studio\nZero-Shot клонирование голоса: сравнение XTTS-v2 vs Chatterbox-Turbo")

    with gr.Row():
        with gr.Column(scale=1):
            # Переключатель движков
            engine_selector = gr.Radio(
                choices=["XTTS (Docker)", "Chatterbox (Local)"],
                value="XTTS (Docker)",
                label="🧠 Движок синтеза",
                info="Выберите модель для генерации речи"
            )

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

            synth_btn = gr.Button(" Синтезировать речь", variant="primary", size="lg")

        with gr.Column(scale=1):
            audio_output = gr.Audio(label="Результат", type="filepath")
            gr.Markdown("---")
            gr.Markdown(
                "###  Советы по качеству\n"
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
        inputs=[engine_selector, voice_dropdown, text_input, speed_slider, temp_slider],
        outputs=audio_output
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())