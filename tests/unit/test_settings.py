from video_agent.config import Settings


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
