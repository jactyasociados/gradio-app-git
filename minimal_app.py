# ~/gradio_test_app/minimal_app.py
import gradio as gr
import os

# Simplified function to mimic getting models
def get_minimal_models():
    print("DEBUG: Getting minimal models")
    # Simulate initial state where no models might be found, then some are.
    if not hasattr(get_minimal_models, "toggle"):
        get_minimal_models.toggle = True
    else:
        get_minimal_models.toggle = not get_minimal_models.toggle

    if get_minimal_models.toggle:
        return ["No Models Found"]
    else:
        return ["deepseek-coder", "deepseek-r1"]


initial_minimal_models = get_minimal_models()
initial_selected_value = initial_minimal_models[0] if initial_minimal_models and initial_minimal_models != ["No Models Found"] else "No Models Found"

with gr.Blocks(title="Minimal Gradio Test") as minimal_ui:
    gr.Markdown("# Minimal Gradio Dropdown Test")

    status_box = gr.Textbox(value=f"Initial Status: {initial_selected_value}", label="Status")

    model_dropdown = gr.Dropdown(
        choices=initial_minimal_models,
        value=initial_selected_value,
        label="Select Model",
        interactive=True
    )

    refresh_button = gr.Button("Refresh Models")

    def refresh_dropdown_and_status():
        print("DEBUG: Refreshing dropdown...")
        updated_models = get_minimal_models()
        new_value = None
        if updated_models and "No Models Found" not in updated_models:
            new_value = updated_models[0]
        elif "No Models Found" in updated_models:
            new_value = "No Models Found"
        
        print(f"DEBUG: Refreshed Models: {updated_models}, New Value: {new_value}")
        return (
            gr.Dropdown.update(choices=updated_models, value=new_value),
            f"Refreshed Status: {new_value if new_value else 'None selected'}"
        )

    refresh_button.click(
        refresh_dropdown_and_status,
        inputs=None,
        outputs=[model_dropdown, status_box]
    )

minimal_ui.launch(server_name="0.0.0.0", server_port=7861)
