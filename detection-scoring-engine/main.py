"""Entry point for the detection service."""
import uvicorn

from detection.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
