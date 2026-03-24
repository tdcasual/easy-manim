import pytest

from fastapi.testclient import TestClient
from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError, SQLiteBootstrapper
from video_agent.config import Settings
from video_agent.server.api_main import build_api_parser
from video_agent.server.http_api import create_http_api


def test_http_api_requires_explicit_database_bootstrap(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "video_agent.db",
        artifact_root=tmp_path / "data" / "tasks",
        run_embedded_worker=False,
    )

    with pytest.raises(DatabaseBootstrapRequiredError):
        create_http_api(settings)


def test_http_api_exposes_health_ready_and_openapi(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "video_agent.db",
        artifact_root=tmp_path / "data" / "tasks",
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    app = create_http_api(settings)
    client = TestClient(app)

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert openapi.json()["info"]["title"] == "easy-manim API"

def test_api_parser_rejects_transport_flag():
    parser = build_api_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--transport", "stdio"])
