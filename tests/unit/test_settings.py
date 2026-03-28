from pathlib import Path

from video_agent.agent_policy import DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
from video_agent.config import Settings
from video_agent.server.main import build_settings


def test_settings_exposes_database_and_artifact_dirs() -> None:
    settings = Settings()
    assert settings.database_path.name == "video_agent.db"
    assert settings.artifact_root.name == "tasks"



def test_settings_exposes_llm_and_worker_runtime_fields() -> None:
    settings = Settings()
    assert settings.llm_provider == "stub"
    assert settings.llm_model == "stub-manim-v1"
    assert settings.llm_api_base is None
    assert settings.llm_timeout_seconds == 60
    assert settings.llm_max_retries == 2
    assert settings.run_embedded_worker is True
    assert settings.worker_poll_interval_seconds == 0.2
    assert settings.worker_lease_seconds == 30
    assert settings.worker_recovery_grace_seconds == 5
    assert settings.worker_stale_after_seconds == 30
    assert settings.max_queued_tasks == 20
    assert settings.max_attempts_per_root_task == 5
    assert settings.auto_repair_retryable_issue_codes == DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES


def test_build_settings_keeps_formula_auto_repair_defaults(monkeypatch) -> None:
    monkeypatch.delenv("EASY_MANIM_AUTO_REPAIR_RETRYABLE_ISSUE_CODES", raising=False)

    settings = build_settings(Path("data"))

    assert settings.auto_repair_retryable_issue_codes == DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES


def test_settings_defaults_to_auth_disabled() -> None:
    settings = Settings()

    assert settings.auth_mode == "disabled"
    assert settings.anonymous_agent_id == "local-anonymous"


def test_build_settings_reads_auth_env(monkeypatch) -> None:
    monkeypatch.setenv("EASY_MANIM_AUTH_MODE", "required")
    monkeypatch.setenv("EASY_MANIM_ANONYMOUS_AGENT_ID", "ops-agent")

    settings = build_settings(Path("data"))

    assert settings.auth_mode == "required"
    assert settings.anonymous_agent_id == "ops-agent"


def test_build_settings_reads_litellm_env(monkeypatch) -> None:
    monkeypatch.setenv("EASY_MANIM_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("EASY_MANIM_LLM_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("EASY_MANIM_LLM_API_BASE", "https://example.test/v1")
    monkeypatch.setenv("EASY_MANIM_LLM_API_KEY", "secret")

    settings = build_settings(Path("data"))

    assert settings.llm_provider == "litellm"
    assert settings.llm_model == "openai/gpt-4.1-mini"
    assert settings.llm_api_base == "https://example.test/v1"
    assert settings.llm_api_key == "secret"


def test_settings_define_session_memory_limits() -> None:
    settings = Settings()

    assert settings.session_memory_max_entries == 5
    assert settings.session_memory_max_attempts_per_entry == 3


def test_settings_define_persistent_memory_defaults() -> None:
    settings = Settings()

    assert settings.persistent_memory_backend == "local"
    assert settings.persistent_memory_enable_embeddings is False
    assert settings.persistent_memory_embedding_provider is None
    assert settings.persistent_memory_embedding_model is None


def test_settings_define_multi_agent_workflow_defaults() -> None:
    settings = Settings()

    assert settings.multi_agent_workflow_enabled is False
    assert settings.multi_agent_workflow_max_child_attempts == 3
    assert settings.multi_agent_workflow_require_completed_for_accept is True


def test_build_settings_reads_multi_agent_workflow_env(monkeypatch) -> None:
    monkeypatch.setenv("EASY_MANIM_MULTI_AGENT_WORKFLOW_ENABLED", "true")
    monkeypatch.setenv("EASY_MANIM_MULTI_AGENT_WORKFLOW_MAX_CHILD_ATTEMPTS", "6")
    monkeypatch.setenv("EASY_MANIM_MULTI_AGENT_WORKFLOW_REQUIRE_COMPLETED_FOR_ACCEPT", "false")

    settings = build_settings(Path("data"))

    assert settings.multi_agent_workflow_enabled is True
    assert settings.multi_agent_workflow_max_child_attempts == 6
    assert settings.multi_agent_workflow_require_completed_for_accept is False
