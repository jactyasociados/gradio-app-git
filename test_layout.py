import gradio as gr
import uvicorn
from fastapi import FastAPI

# Simple CSS to ensure columns are flex items
app_css = """
.gradio-container { max-width: 1200px; margin: auto; }
.main-layout-row {
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
    gap: 10px; /* Space between columns */
    padding: 10px;
    background-color: #f0f0f0; /* See the row boundaries */
}
#left_test_column {
    width: 70%;
    min-width: 400px;
    background-color: #e0ffe0; /* See left column boundaries */
    padding: 10px;
    box-sizing: border-box;
    flex-grow: 1;
    flex-shrink: 1;
}
#right_test_column {
    width: 30%;
    min-width: 250px;
    background-color: #ffe0e0; /* See right column boundaries */
    padding: 10px;
    box-sizing: border-box;
    flex-grow: 0;
    flex-shrink: 0;
}
"""

with gr.Blocks(theme="soft", title="Layout Test", css=app_css) as test_ui:
    gr.Markdown("# Gradio Column Layout Test")
    gr.Markdown("---") # Visual separator

    with gr.Row(elem_id="main_layout_row"):
        with gr.Column(scale=3, min_width=400, elem_id="left_test_column"):
            gr.Markdown("### Left Column")
            gr.Textbox("This is the left column content.", interactive=False)
            gr.Slider(minimum=0, maximum=10, value=5, label="Left Slider")
            gr.Markdown("---")
            gr.Button("Left Button")

        with gr.Column(scale=1, min_width=250, elem_id="right_test_column"):
            gr.Markdown("### Right Column")
            gr.Textbox("This is the right column content, it MUST be visible!", interactive=False)
            gr.Dropdown(["Option A", "Option B"], label="Right Dropdown")
            gr.Markdown("---")
            gr.Button("Right Button")

_main_app = FastAPI()
application = gr.mount_gradio_app(_main_app, test_ui, path="/")

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=7860)
