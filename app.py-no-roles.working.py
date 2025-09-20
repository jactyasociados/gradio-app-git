import gradio as gr
import requests
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:latest")

# Ensure DEFAULT_OLLAMA_MODEL is always a string, even if env var is missing/empty
if not DEFAULT_OLLAMA_MODEL:
    DEFAULT_OLLAMA_MODEL = "deppseek-coder:latest" # Fallback to a very common default if deepseek-coder is also not set

# Define the timeout value for Ollama requests
REQUEST_TIMEOUT = 1200 # seconds

def get_available_ollama_models():
    """Fetches a list of locally available Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        data = response.json()
        models = [m['name'] for m in data.get('models', [])]
        return models
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama server at {OLLAMA_HOST} to fetch models.")
        return [] # Return empty list on connection error
    except requests.exceptions.Timeout:
        print(f"Error: Ollama server at {OLLAMA_HOST} timed out while fetching models.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Ollama models: {e}")
        return []
    except json.JSONDecodeError:
        print("Error: Received an invalid JSON response when fetching Ollama models.")
        return []

# Get initial list of models
_initial_available_models_raw = get_available_ollama_models()

# Ensure DEFAULT_OLLAMA_MODEL is always an option and is at the top if available
if DEFAULT_OLLAMA_MODEL not in _initial_available_models_raw:
    _initial_available_models_raw.insert(0, DEFAULT_OLLAMA_MODEL) # Add default if not present
elif _initial_available_models_raw and _initial_available_models_raw[0] != DEFAULT_OLLAMA_MODEL:
    # If default is in list but not first, move it to first
    _initial_available_models_raw.remove(DEFAULT_OLLAMA_MODEL)
    _initial_available_models_raw.insert(0, DEFAULT_OLLAMA_MODEL)

# If still empty (e.g., Ollama not running and DEFAULT_OLLAMA_MODEL was not in tags), fallback
if not _initial_available_models_raw:
    _initial_available_models_raw = [DEFAULT_OLLAMA_MODEL]

available_models = _initial_available_models_raw
initial_selected_model = available_models[0] # The model to be initially selected

print(f"DEBUG: Initial available_models for Gradio: {available_models}")
print(f"DEBUG: Initial selected model for Gradio: {initial_selected_model}")


def get_ollama_response(prompt, history, selected_model):
    """
    Function to interact with the Ollama API.
    Now accepts 'selected_model' as an argument.
    """
    messages = []
    for human_msg, ai_msg in history:
        messages.append({"role": "user", "content": human_msg})
        messages.append({"role": "assistant", "content": ai_msg})
    messages.append({"role": "user", "content": prompt})

    # Use the selected_model, or fallback to default if somehow not set
    model_to_use = selected_model if selected_model else initial_selected_model # Use initial_selected_model as fallback

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            headers={"Content-Type": "application/json"},
            json={
                "model": model_to_use,
                "messages": messages,
                "stream": False
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data['message']['content']
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to Ollama server at {OLLAMA_HOST}. Please ensure it is running and accessible."
    except requests.exceptions.Timeout:
        return f"Error: Ollama server at {OLLAMA_HOST} timed out after {REQUEST_TIMEOUT} seconds. Model might be loading or response is very slow."
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
             return f"Error communicating with Ollama: HTTP {e.response.status_code} - {e.response.text}"
        return f"Error communicating with Ollama: {e}"
    except json.JSONDecodeError:
        return "Error: Received an invalid JSON response from Ollama."


# Custom CSS for the layout
app_css = """
.gradio-container { max-width: 1200px; margin: auto; }
.main-layout-row {
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
    gap: 10px; /* Space between columns */
    padding: 10px;
}
#left_chatbot_column {
    flex-grow: 3; /* Chatbot takes more space */
    min-width: 400px;
    padding: 10px;
    box-sizing: border-box;
}
#right_controls_column {
    flex-grow: 1; /* Controls take less space */
    min-width: 250px;
    max-width: 350px; /* Optional: cap the width for controls */
    padding: 10px;
    box-sizing: border-box;
    display: flex; /* Make it a flex container */
    flex-direction: column; /* Stack children vertically */
    gap: 10px; /* Space between elements in the column */
}
"""

# Build the Gradio UI using gr.Blocks
with gr.Blocks(theme="soft", title="Ollama Gradio Chatbot", css=app_css) as chatbot_ui:
    gr.Markdown(f"# Ollama Gradio Chatbot ({OLLAMA_HOST})")
    gr.Markdown(f"Chat with the selected Ollama model.")

    with gr.Row(elem_id="main_layout_row"):
        with gr.Column(elem_id="left_chatbot_column"):
            # Manual Chatbot Components
            chatbot = gr.Chatbot(height=500, elem_id="chatbot_component")
            msg = gr.Textbox(placeholder="Ask me anything...", container=False, scale=7, elem_id="textbox_component")
            
            with gr.Row():
                submit_btn = gr.Button("Submit", variant="primary", scale=1)
                clear_btn = gr.Button("Clear") 
                retry_btn = gr.Button("Retry")
                undo_btn = gr.Button("Undo")

        with gr.Column(elem_id="right_controls_column"):
            gr.Markdown("### Settings")
            model_state = gr.State(value=initial_selected_model) # Use the robust initial_selected_model

            model_dropdown = gr.Dropdown(
                choices=available_models,
                value=initial_selected_model, # Use the robust initial_selected_model
                label="Select Ollama Model",
                interactive=True,
                elem_id="model_dropdown_component"
            )
            
            gr.Markdown("---")
            gr.Markdown("More controls could go here...")
            refresh_models_btn = gr.Button("Refresh Models", elem_id="refresh_models_button")

        # Event Handlers
        def user_message(user_message_text, history):
            if user_message_text is None or user_message_text.strip() == "":
                return "", history # Don't add empty messages
            return "", history + [[user_message_text, None]]

        def bot_response(history, selected_model_value):
            if not history or (len(history) > 0 and history[-1][1] is not None): # If no history or last bot response already generated
                return history
            
            user_message = history[-1][0]
            # The history passed to get_ollama_response should exclude the current partial message
            ollama_history = history[:-1] 
            
            bot_message = get_ollama_response(user_message, ollama_history, selected_model_value)
            history[-1][1] = bot_message
            return history

        # Update model_state when dropdown changes
        model_dropdown.change(fn=lambda x: x, inputs=model_dropdown, outputs=model_state)

        # Main chat submission logic
        msg.submit(
            user_message, 
            [msg, chatbot], 
            [msg, chatbot], 
            queue=False # Important for responsiveness
        ).then(
            bot_response, 
            [chatbot, model_state], 
            chatbot
        )
        submit_btn.click(
            user_message, 
            [msg, chatbot], 
            [msg, chatbot], 
            queue=False
        ).then(
            bot_response, 
            [chatbot, model_state], 
            chatbot
        )

        clear_btn.click(lambda: (None, None), None, [msg, chatbot], queue=False)
        
        def retry_last_message(history, selected_model_value):
            if not history:
                return []
            
            # Remove the last bot response (if any) and re-process the last user message
            last_user_message = history[-1][0]
            processed_history = history[:-1] # Remove last exchange
            
            return bot_response(processed_history + [[last_user_message, None]], selected_model_value)

        retry_btn.click(
            retry_last_message, [chatbot, model_state], chatbot
        )

        def undo_last_message(history):
            if not history:
                return history
            return history[:-1] # Remove the last turn (user message + bot response)

        undo_btn.click(
            undo_last_message, chatbot, chatbot
        )
        
        refresh_models_btn.click(
            fn=get_available_ollama_models,
            outputs=model_dropdown
        )


# Create a FastAPI app
_main_app = FastAPI()

# Mount the Gradio app to the FastAPI app
application = gr.mount_gradio_app(_main_app, chatbot_ui, path="/")

# For direct execution during development/testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=7860)
