from pathlib import Path

from PIL import Image

from video_agent.validation.preview_quality import PreviewQualityValidator


def _solid(path: Path, rgb: tuple[int, int, int]) -> None:
    Image.new("RGB", (320, 180), rgb).save(path)


def test_preview_quality_flags_near_blank_sequence(tmp_path: Path) -> None:
    frame_a = tmp_path / "frame_001.png"
    frame_b = tmp_path / "frame_002.png"
    _solid(frame_a, (0, 0, 0))
    _solid(frame_b, (0, 0, 0))

    report = PreviewQualityValidator().validate([frame_a, frame_b], profile={})

    assert report.passed is False
    assert any(issue.code == "near_blank_preview" for issue in report.issues)


def test_preview_quality_flags_static_sequence(tmp_path: Path) -> None:
    frame_a = tmp_path / "frame_001.png"
    frame_b = tmp_path / "frame_002.png"
    _solid(frame_a, (200, 200, 200))
    _solid(frame_b, (200, 200, 200))

    report = PreviewQualityValidator().validate([frame_a, frame_b], profile={"check_static_previews": True})

    assert any(issue.code == "static_previews" for issue in report.issues)


def test_preview_quality_accepts_sequences_with_clear_mid_scene_motion(tmp_path: Path) -> None:
    frame_a = tmp_path / "frame_001.png"
    frame_b = tmp_path / "frame_002.png"
    frame_c = tmp_path / "frame_003.png"
    _solid(frame_a, (200, 200, 200))
    _solid(frame_b, (80, 80, 80))
    _solid(frame_c, (200, 200, 200))

    report = PreviewQualityValidator().validate(
        [frame_a, frame_b, frame_c],
        profile={"check_static_previews": True},
    )

    assert not any(issue.code == "static_previews" for issue in report.issues)
