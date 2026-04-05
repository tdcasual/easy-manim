import importlib
import importlib.util
from types import SimpleNamespace

from fastapi import FastAPI


MODULE_NAME = "video_agent.server.http_api_video_thread_routes"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_register_video_thread_routes_exposes_thread_surface_iteration_and_participant_paths() -> None:
    module = _load_module()
    app = FastAPI()

    module.register_video_thread_routes(
        app=app,
        context=SimpleNamespace(),
        resolve_optional_agent_session=lambda request, authorization: None,
    )

    routes = {(method, route.path) for route in app.routes for method in route.methods or []}

    assert ("POST", "/api/video-threads") in routes
    assert ("GET", "/api/video-threads/{thread_id}") in routes
    assert ("GET", "/api/video-threads/{thread_id}/surface") in routes
    assert ("GET", "/api/video-threads/{thread_id}/iterations/{iteration_id}") in routes
    assert ("POST", "/api/video-threads/{thread_id}/turns") in routes
    assert ("POST", "/api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision") in routes
    assert ("POST", "/api/video-threads/{thread_id}/iterations/{iteration_id}/request-explanation") in routes
    assert ("POST", "/api/video-threads/{thread_id}/iterations/{iteration_id}/select-result") in routes
    assert ("GET", "/api/video-threads/{thread_id}/participants") in routes
    assert ("POST", "/api/video-threads/{thread_id}/participants") in routes
    assert ("DELETE", "/api/video-threads/{thread_id}/participants/{participant_id}") in routes
