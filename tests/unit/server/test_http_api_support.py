import pytest
from fastapi import HTTPException

from video_agent.server.http_api_support import (
    allowed_task_artifact_resource_uri,
    download_url_from_resource_uri,
    strip_internal_session_fields,
)


def test_allowed_task_artifact_resource_uri_accepts_known_artifacts() -> None:
    assert (
        allowed_task_artifact_resource_uri("task-123", "final_video.mp4")
        == "video-task://task-123/artifacts/final_video.mp4"
    )
    assert (
        allowed_task_artifact_resource_uri("task-123", "previews/frame_001.png")
        == "video-task://task-123/artifacts/previews/frame_001.png"
    )
    assert (
        allowed_task_artifact_resource_uri("task-123", "validations/report.json")
        == "video-task://task-123/validations/report.json"
    )


@pytest.mark.parametrize("artifact_path", ["", "../secret.txt", "/tmp/secret.txt", "artifacts/hidden.txt"])
def test_allowed_task_artifact_resource_uri_rejects_unsafe_paths(artifact_path: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        allowed_task_artifact_resource_uri("task-123", artifact_path)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "resource_not_found"


def test_download_url_from_resource_uri_normalizes_artifact_prefix() -> None:
    assert (
        download_url_from_resource_uri("video-task://task-123/artifacts/final_video.mp4")
        == "/api/tasks/task-123/artifacts/final_video.mp4"
    )
    assert (
        download_url_from_resource_uri("video-task://task-123/validations/report.json")
        == "/api/tasks/task-123/artifacts/validations/report.json"
    )
    assert download_url_from_resource_uri("https://example.com/file.mp4") is None


def test_strip_internal_session_fields_recurses_into_items() -> None:
    payload = {
        "session_id": "session-1",
        "source_session_id": "source-1",
        "items": [
            {"session_id": "nested-session", "value": 1},
            {"source_session_id": "nested-source", "value": 2},
            "keep-me",
        ],
        "value": 3,
    }

    assert strip_internal_session_fields(payload) == {
        "items": [
            {"value": 1},
            {"value": 2},
            "keep-me",
        ],
        "value": 3,
    }
