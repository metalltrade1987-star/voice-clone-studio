import gradio as gr
from pathlib import Path
from src.chatterbox_engine import ChatterboxVoiceCloner

# На HF используем только локальный Chatterbox
cloner = ChatterboxVoiceCloner()


def synthesize_hf(voice_file, text, speed, temperature):
    if not voice_file or not text.strip():
        raise gr.Error("Загрузите голос и введите текст!")

    # voice_file на HF - это временный путь загруженного файла
    output_path = f"output_{Path(voice_file).stem}.wav"

    return cloner.synthesize(
        reference_path=voice_file,
        text=text,
        output_path=output_path,
        speed=speed,
        temperature=temperature
    )


with gr.Blocks(title="Voice Clone Studio | Chatterbox V3 Demo") as demo:
    gr.Markdown("# 🎙️ Voice Clone Studio\nZero-Shot клонирование голоса на Chatterbox Multilingual V3")

    with gr.Row():
        with gr.Column():
            voice_input = gr.Audio(label="Эталонный голос", type="filepath")
            text_input = gr.Textbox(label="Текст", lines=4, placeholder="Введите русский текст...")

            with gr.Accordion("Настройки", open=False):
                speed = gr.Slider(0.5, 1.5, value=0.9, label="Скорость")
                temp = gr.Slider(0.3, 1.0, value=0.7, label="Выразительность")

            btn = gr.Button("Синтезировать", variant="primary")

        with gr.Column():
            audio_out = gr.Audio(label="Результат")

    btn.click(synthesize_hf, [voice_input, text_input, speed, temp], audio_out)

if __name__ == "__main__":
    demo.launch()