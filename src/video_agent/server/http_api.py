from fastapi import FastAPI

from video_agent.config import Settings
from video_agent.server.app import create_app_context


def create_http_api(settings: Settings) -> FastAPI:
    context = create_app_context(settings)
    app = FastAPI(title="easy-manim API", version="0.1.0")
    app.state.app_context = context

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    return app
