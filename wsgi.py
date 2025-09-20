# /var/www/gradio-app/wsgi.py
from app import application # Import the 'application' object directly from app.py

# The 'application' variable from app.py is already the *actual* ASGI application.
# No need for `.app` attribute access anymore.
# application = _app_blocks.app # REMOVE THIS LINE

# The if __name__ == "__main__": block is typically not executed by Gunicorn
# but if you want to be able to run `python wsgi.py` for local testing:
if __name__ == "__main__":
    import uvicorn
    # When running directly, you would launch the Gradio blocks directly.
    # Uvicorn would then internally use application
    uvicorn.run(application, host="0.0.0.0", port=7860)
