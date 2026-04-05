import importlib
import importlib.util
from types import SimpleNamespace

from fastapi import FastAPI


MODULE_NAME = "video_agent.server.http_api_profile_memory_routes"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_register_profile_memory_routes_exposes_profile_and_memory_paths() -> None:
    module = _load_module()
    app = FastAPI()

    module.register_profile_memory_routes(
        app=app,
        context=SimpleNamespace(),
        profile_suggestion_service=SimpleNamespace(),
        suggestion_payload=lambda item: item,
        strategy_profile_payload=lambda item: item,
        require_accessible_session_summary=lambda session_id, agent_id: None,
        raise_persistent_memory_http_error=lambda exc: None,
    )

    routes = {(method, route.path) for route in app.routes for method in route.methods or []}

    assert ("GET", "/api/profile/strategies") in routes
    assert ("GET", "/api/profile/evals") in routes
    assert ("GET", "/api/profile/evals/{run_id}") in routes
    assert ("GET", "/api/profile/strategy-decisions") in routes
    assert ("POST", "/api/profile/apply") in routes
    assert ("POST", "/api/profile/preferences/propose") in routes
    assert ("POST", "/api/profile/preferences/promote") in routes
    assert ("POST", "/api/profile/suggestions/generate") in routes
    assert ("GET", "/api/profile/suggestions") in routes
    assert ("POST", "/api/profile/suggestions/{suggestion_id}/apply") in routes
    assert ("POST", "/api/profile/suggestions/{suggestion_id}/dismiss") in routes
    assert ("GET", "/api/memory/session") in routes
    assert ("GET", "/api/memory/session/summary") in routes
    assert ("DELETE", "/api/memory/session") in routes
    assert ("POST", "/api/memories/promote") in routes
    assert ("GET", "/api/memories") in routes
    assert ("POST", "/api/memories/retrieve") in routes
    assert ("GET", "/api/memories/{memory_id}") in routes
    assert ("POST", "/api/memories/{memory_id}/disable") in routes
