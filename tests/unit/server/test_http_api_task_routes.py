import importlib
import importlib.util
from types import SimpleNamespace

from fastapi import FastAPI


MODULE_NAME = "video_agent.server.http_api_task_routes"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_register_task_routes_exposes_task_review_workflow_and_artifact_paths() -> None:
    module = _load_module()
    app = FastAPI()

    module.register_task_routes(app=app, context=SimpleNamespace())

    routes = {(method, route.path) for route in app.routes for method in route.methods or []}

    assert ("POST", "/api/tasks") in routes
    assert ("GET", "/api/tasks") in routes
    assert ("GET", "/api/tasks/{task_id}") in routes
    assert ("GET", "/api/tasks/{task_id}/scene-spec") in routes
    assert ("GET", "/api/tasks/{task_id}/recovery-plan") in routes
    assert ("GET", "/api/tasks/{task_id}/quality-score") in routes
    assert ("GET", "/api/tasks/{task_id}/result") in routes
    assert ("GET", "/api/tasks/{task_id}/review-bundle") in routes
    assert ("GET", "/api/tasks/{task_id}/discussion-thread") in routes
    assert ("POST", "/api/tasks/{task_id}/review-decision") in routes
    assert ("POST", "/api/tasks/{task_id}/discussion-messages") in routes
    assert ("GET", "/api/tasks/{task_id}/workflow-participants") in routes
    assert ("POST", "/api/tasks/{task_id}/workflow-participants") in routes
    assert ("DELETE", "/api/tasks/{task_id}/workflow-participants/{agent_id}") in routes
    assert ("GET", "/api/tasks/{task_id}/workflow-memory/recommendations") in routes
    assert ("POST", "/api/tasks/{task_id}/workflow-memory/pins") in routes
    assert ("DELETE", "/api/tasks/{task_id}/workflow-memory/pins/{memory_id}") in routes
    assert ("GET", "/api/videos/recent") in routes
    assert ("GET", "/api/tasks/{task_id}/artifacts/{artifact_path:path}") in routes
    assert ("POST", "/api/tasks/{task_id}/revise") in routes
    assert ("POST", "/api/tasks/{task_id}/retry") in routes
    assert ("POST", "/api/tasks/{task_id}/cancel") in routes
    assert ("POST", "/api/tasks/{task_id}/accept-best") in routes
