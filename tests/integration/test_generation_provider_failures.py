import json

import video_agent.server.app as app_module
from video_agent.adapters.llm.client import StubLLMClient
from video_agent.adapters.llm.openai_compatible_client import ProviderAuthError
from video_agent.config import Settings
from video_agent.server.app import create_app_context


class FailingLLMClient:
    def generate_script(self, prompt_text: str) -> str:
        raise ProviderAuthError("bad key")



def _settings(tmp_path, **overrides) -> Settings:
    data_dir = tmp_path / "data"
    values = {
        "data_dir": data_dir,
        "database_path": data_dir / "video_agent.db",
        "artifact_root": data_dir / "tasks",
        "llm_provider": "stub",
        "llm_model": "stub-manim-v1",
    }
    values.update(overrides)
    return Settings(**values)



def test_create_app_context_uses_stub_provider_by_default(tmp_path) -> None:
    app = create_app_context(_settings(tmp_path))
    assert isinstance(app.workflow_engine.llm_client, StubLLMClient)



def test_generation_auth_failure_becomes_standardized_validation_issue(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: FailingLLMClient(), raising=False)
    settings = _settings(
        tmp_path,
        llm_provider="openai_compatible",
        llm_model="gpt-4.1-mini",
        llm_base_url="https://example.test/v1",
        llm_api_key="secret",
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "provider_auth_error"


def test_generation_auth_failure_writes_failure_context_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_build_llm_client", lambda settings: FailingLLMClient(), raising=False)
    settings = _settings(
        tmp_path,
        llm_provider="openai_compatible",
        llm_model="gpt-4.1-mini",
        llm_base_url="https://example.test/v1",
        llm_api_key="secret",
    )
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    failure_context_path = app.artifact_store.task_dir(created.task_id) / "artifacts" / "failure_context.json"
    payload = json.loads(failure_context_path.read_text())

    assert payload["task_id"] == created.task_id
    assert payload["failure_code"] == "provider_auth_error"
    assert payload["summary"] == "Provider authentication failed"
    assert payload["provider_error"] == "bad key"
    assert payload["current_script_resource"] is None
