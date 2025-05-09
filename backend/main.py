import logging
from logging.config import dictConfig
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from backend.routers.filters import router as filters_router
from backend.routers.user import router as users_router

# Logging configuration
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": "app.log",
            "mode": "a"
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console", "file"]
    }
}

dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Absolute path to project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Mount static files directory
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static"
)

# Serve main index.html
@app.get("/")
def main():
    return FileResponse(BASE_DIR / "frontend" / "templates" / "index.html")

# Register routers
app.include_router(users_router)
app.include_router(filters_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
