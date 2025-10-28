import uvicorn
import os

def main():
    """
    Starts the Uvicorn server for the FastAPI application.

    It looks for the FastAPI app instance in `app.ui.ws:app`.
    The server will reload automatically when code changes are detected.
    """
    # It's good practice to set the app directory in the python path
    # This ensures that all module imports work as expected from the root
    sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app'))
    if sys_path not in os.environ.get('PYTHONPATH', ''):
        os.environ['PYTHONPATH'] = f"{sys_path}:{os.environ.get('PYTHONPATH', '')}"

    print("Starting Uvicorn server...")
    print("Access the UI at http://127.0.0.1:8000")

    uvicorn.run("app.ui.ws:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
