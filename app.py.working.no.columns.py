# /var/www/gradio-app/app.py
import gradio as gr
import requests
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
import asyncio

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder")

# --- Function to get available Ollama models ---
def get_available_ollama_models():
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        
        if DEFAULT_OLLAMA_MODEL not in models:
            models.insert(0, DEFAULT_OLLAMA_MODEL)
        
        if not models:
            models = [DEFAULT_OLLAMA_MODEL]
            
        print(f"DEBUG: Available Models: {models}")
        return models
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch Ollama models from {OLLAMA_HOST}/api/tags. Error: {e}")
        return [DEFAULT_OLLAMA_MODEL]

AVAILABLE_MODELS = get_available_ollama_models()

def get_ollama_response(prompt, history, selected_model):
    messages = []
    for human_msg, ai_msg in history:
        messages.append({"role": "user", "content": human_msg})
        messages.append({"role": "assistant", "content": ai_msg})
    messages.append({"role": "user", "content": prompt})

    model_to_use = selected_model if selected_model else DEFAULT_OLLAMA_MODEL
    
    if not model_to_use or (model_to_use not in AVAILABLE_MODELS and AVAILABLE_MODELS):
        model_to_use = AVAILABLE_MODELS[0] if AVAILABLE_MODELS else DEFAULT_OLLAMA_MODEL
    
    if not AVAILABLE_MODELS or model_to_use == "No Models Found":
        return "Error: No Ollama models found or configured. Please check your Ollama server and its models."

    request_timeout = 1200

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            headers={"Content-Type": "application/json"},
            json={
                "model": model_to_use,
                "messages": messages,
                "stream": False
            },
            timeout=request_timeout
        )
        response.raise_for_status()
        data = response.json()
        return data['message']['content']
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to Ollama server at {OLLAMA_HOST}. Please ensure it is running and accessible."
    except requests.exceptions.Timeout:
        return f"Error: Ollama server at {OLLAMA_HOST} timed out after {request_timeout} seconds. Model might be loading or response is very slow."
    except requests.exceptions.RequestException as e:
        if 'response' in locals() and hasattr(response, 'status_code'):
             return f"Error communicating with Ollama: HTTP {response.status_code} - {response.text}"
        return f"Error communicating with Ollama: {e}"
    except json.JSONDecodeError:
        return "Error: Received an invalid JSON response from Ollama."


# The main Gradio Blocks object for the UI
# Re-applying the *working* CSS from test_layout.py
app_css = """
body { margin: 0; padding: 0; }
.gradio-container { 
    max-width: 1200px; 
    margin: 20px auto; 
    border: 2px solid #ccc; /* Subtle outline for the main container */
    padding: 10px;
}

/* Force the gr.Row to be a horizontal flex container */
#main_layout_row {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important; /* PREVENT wrapping to new lines */
    width: 100% !important;
    min-height: 400px; /* Ensure row has a minimum height */
    gap: 15px !important; /* Explicit space between columns */
    padding: 15px !important;
    background-color: #f8f8f8; /* Light gray to see the row boundaries */
    border: 1px solid #eee !important; /* Outline the row */
    align-items: stretch !important; /* Make columns fill height of row */
}

/* Explicitly set widths and flex properties for columns */
#chat_column {
    background-color: #ffffff !important; /* White background for chat */
    padding: 15px !important;
    border: 1px solid #e0e0e0 !important; /* Outline left column */
    box-sizing: border-box !important;
    flex: 3 1 400px !important; /* flex-grow, flex-shrink, flex-basis */
    min-width: 400px !important;
}
#model_selection_column {
    background-color: #f9f9f9 !important; /* Slightly off-white for model select */
    padding: 15px !important;
    border: 1px solid #e0e0e0 !important; /* Outline right column */
    box-sizing: border-box !important;
    flex: 1 0 250px !important; /* flex-grow, flex-shrink, flex-basis */
    min-width: 250px !important;
}

/* General Gradio column styling, less important than specific IDs */
.gradio-column {
    padding: 10px;
    margin: 0; /* Reset margins */
    box-sizing: border-box;
}
"""

with gr.Blocks(theme="soft", title="Ollama Gradio Chatbot", css=app_css) as chatbot_ui:
    gr.Markdown(f"# Ollama Gradio Chatbot")
    gr.Markdown(f"Chat with Ollama ({OLLAMA_HOST})")

    if not AVAILABLE_MODELS or (AVAILABLE_MODELS == [DEFAULT_OLLAMA_MODEL] and DEFAULT_OLLAMA_MODEL == "deepseek-coder"):
        gr.Info(f"Warning: No Ollama models found or default '{DEFAULT_OLLAMA_MODEL}' is the only one. Please ensure Ollama server is running and models are downloaded. Check `ollama.service` logs for details. Initial Models: {AVAILABLE_MODELS}")
        if not AVAILABLE_MODELS or (AVAILABLE_MODELS == [DEFAULT_OLLAMA_MODEL] and DEFAULT_OLLAMA_MODEL == "deepseek-coder"):
            DEFAULT_OLLAMA_MODEL = "No Models Found"
            AVAILABLE_MODELS = ["No Models Found"]

    with gr.Row(elem_id="main_layout_row"): 
        with gr.Column(
            scale=3, 
            min_width=400, 
            elem_id="chat_column"
        ): 
            chatbot = gr.Chatbot(height=500, label="Chat History")
            msg = gr.Textbox(
                show_label=False,
                placeholder="Ask me anything...",
                container=False,
                autofocus=True
            )
            with gr.Row():
                submit_btn = gr.Button("Submit", variant="primary")
                clear_btn = gr.ClearButton([msg, chatbot])

        with gr.Column(
            scale=1, 
            min_width=250, 
            elem_id="model_selection_column"
        ): 
            gr.Markdown("### Model Selection") 
            gr.Textbox(
                value="If this text is visible, the right column is rendering correctly.", 
                interactive=False, 
                label="Column Debugger"
            )

            model_selector_initial_value = None
            if AVAILABLE_MODELS and (DEFAULT_OLLAMA_MODEL in AVAILABLE_MODELS or "No Models Found" in AVAILABLE_MODELS):
                model_selector_initial_value = DEFAULT_OLLAMA_MODEL
            elif AVAILABLE_MODELS:
                model_selector_initial_value = AVAILABLE_MODELS[0]

            model_selector = gr.Dropdown(
                choices=AVAILABLE_MODELS,
                value=model_selector_initial_value,
                label="Select Ollama Model",
                interactive=True
            )
            
            initial_model_display_value = f"Current Model: {model_selector.value if model_selector.value else 'None selected'}"

            selected_model_display = gr.Textbox(
                value=initial_model_display_value,
                interactive=False,
                label="Selected Model"
            )
            refresh_models_btn = gr.Button("Refresh Model List")
            
            def refresh_and_update_display():
                updated_models = get_available_ollama_models()
                new_default_value = None
                if updated_models and ("No Models Found" not in updated_models):
                    if DEFAULT_OLLAMA_MODEL in updated_models:
                        new_default_value = DEFAULT_OLLAMA_MODEL
                    else:
                        new_default_value = updated_models[0]
                elif "No Models Found" in updated_models:
                    new_default_value = "No Models Found"
                    
                return updated_models, f"Current Model: {new_default_value if new_default_value else 'None selected'}"

            model_selector.change(
                lambda x: f"Current Model: {x}",
                inputs=model_selector,
                outputs=selected_model_display
            )

            refresh_models_btn.click(
                refresh_and_update_display,
                inputs=None,
                outputs=[model_selector, selected_model_display],
                queue=False
            )


    def chat_submit(prompt, history, selected_model):
        if not prompt:
            return "", history
        
        if not AVAILABLE_MODELS or selected_model == "No Models Found":
            return "", history + [[prompt, "Error: No Ollama models found. Cannot chat. Please refresh the model list or check Ollama server."]]

        response = get_ollama_response(prompt, history, selected_model)
        return "", history + [[prompt, response]]

    submit_btn.click(
        chat_submit,
        inputs=[msg, chatbot, model_selector],
        outputs=[msg, chatbot],
        queue=True
    )
    msg.submit(
        chat_submit,
        inputs=[msg, chatbot, model_selector],
        outputs=[msg, chatbot],
        queue=True
    )


_main_app = FastAPI()
application = gr.mount_gradio_app(_main_app, chatbot_ui, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=7861)
