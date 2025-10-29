import uvicorn
import os

if __name__ == "__main__":
    # Ensure the ENCRYPTION_KEY is set for the db models
    if not os.getenv("ENCRYPTION_KEY"):
        print("Warning: ENCRYPTION_KEY not set. Using a temporary key.")
        # In a real app, you'd require this to be set.

    uvicorn.run("app.ui.ws:app", host="0.0.0.0", port=8000, reload=False)
