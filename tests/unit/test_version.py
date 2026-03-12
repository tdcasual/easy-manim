from video_agent.version import get_release_metadata


def test_get_release_metadata_exposes_version_and_channel() -> None:
    metadata = get_release_metadata()

    assert metadata["version"]
    assert metadata["channel"] in {"beta", "rc", "stable"}
