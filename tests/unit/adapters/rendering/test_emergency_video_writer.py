from pathlib import Path

import pytest

from video_agent.adapters.rendering.emergency_video_writer import (
    EmergencyVideoWriteError,
    EmergencyVideoWriter,
)


def test_emergency_video_writer_replaces_target_only_after_validation_passes(tmp_path: Path) -> None:
    target = tmp_path / "final_video.mp4"
    original_bytes = b"old-video"
    target.write_bytes(original_bytes)
    validator_inputs: list[Path] = []

    def _validator(candidate: Path) -> bool:
        validator_inputs.append(candidate)
        assert candidate != target
        assert target.read_bytes() == original_bytes
        return True

    writer = EmergencyVideoWriter(command="definitely-missing-ffmpeg", validator=_validator)

    result = writer.write(target)

    assert result == target
    assert validator_inputs
    assert target.read_bytes() != original_bytes
    assert not list(tmp_path.glob("*.tmp"))


def test_emergency_video_writer_preserves_existing_target_when_validation_fails(tmp_path: Path) -> None:
    target = tmp_path / "final_video.mp4"
    original_bytes = b"old-video"
    target.write_bytes(original_bytes)

    writer = EmergencyVideoWriter(command="definitely-missing-ffmpeg", validator=lambda _path: False)

    with pytest.raises(EmergencyVideoWriteError) as exc:
        writer.write(target)

    assert exc.value.reason == "invalid_emergency_video"
    assert target.read_bytes() == original_bytes
    assert not list(tmp_path.glob("*.tmp"))
