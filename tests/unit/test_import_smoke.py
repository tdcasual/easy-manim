from video_agent.config import Settings


def test_settings_has_default_data_dir() -> None:
    settings = Settings()
    assert str(settings.data_dir).endswith("data")
