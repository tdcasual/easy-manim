import importlib
import importlib.util
from types import SimpleNamespace

from fastapi import FastAPI


MODULE_NAME = "video_agent.server.http_api_identity_routes"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_register_identity_routes_exposes_runtime_session_and_profile_paths() -> None:
    module = _load_module()
    app = FastAPI()

    module.register_identity_routes(app=app, context=SimpleNamespace())

    routes = {(method, route.path) for route in app.routes for method in route.methods or []}

    assert ("GET", "/healthz") in routes
    assert ("GET", "/readyz") in routes
    assert ("GET", "/api/runtime/status") in routes
    assert ("POST", "/api/sessions") in routes
    assert ("GET", "/api/whoami") in routes
    assert ("DELETE", "/api/sessions/current") in routes
    assert ("GET", "/api/profile") in routes
    assert ("GET", "/api/profile/scorecard") in routes
