from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_http_memory_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            persistent_memory_backend="local",
            persistent_memory_enable_embeddings=False,
        )
    )


def _seed_agent_profile_and_token(client: TestClient) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )


def test_memory_retrieval_endpoint_returns_ranked_active_memories(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_memory_settings(tmp_path)))
    _seed_agent_profile_and_token(client)
    token = client.post("/api/sessions", json={"agent_token": "agent-a-secret"}).json()["session_token"]

    context = client.app.state.app_context
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-a",
            status="active",
            summary_text="Dark background with smooth transitions and easing.",
            summary_digest="digest-a",
        )
    )
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-b",
            agent_id="agent-a",
            source_session_id="session-b",
            status="active",
            summary_text="Typography pacing and subtitle timing guidance.",
            summary_digest="digest-b",
        )
    )
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-c",
            agent_id="agent-a",
            source_session_id="session-c",
            status="disabled",
            summary_text="Dark background fallback guidance.",
            summary_digest="digest-c",
        )
    )

    response = client.post(
        "/api/memories/retrieve",
        json={"query": "dark transitions", "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["memory_id"] for item in payload["items"]] == ["mem-a"]
    assert payload["items"][0]["score"] > 0
    assert "source_session_id" not in payload["items"][0]


def test_memory_retrieval_works_without_embeddings_for_local_backend(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_memory_settings(tmp_path)))
    _seed_agent_profile_and_token(client)
    token = client.post("/api/sessions", json={"agent_token": "agent-a-secret"}).json()["session_token"]

    created = client.post(
        "/api/tasks",
        json={"prompt": "Use a dark background and smooth transitions."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 200

    promoted = client.post("/api/memories/promote", headers={"Authorization": f"Bearer {token}"})
    assert promoted.status_code == 200
    assert promoted.json()["enhancement"]["retrieval"]["tokens"]

    retrieved = client.post(
        "/api/memories/retrieve",
        json={"query": "dark background", "limit": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retrieved.status_code == 200
    assert retrieved.json()["items"]
