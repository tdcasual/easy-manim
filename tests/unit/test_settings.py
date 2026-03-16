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


def test_settings_define_session_memory_limits() -> None:
    settings = Settings()

    assert settings.session_memory_max_entries == 5
    assert settings.session_memory_max_attempts_per_entry == 3
