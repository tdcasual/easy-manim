from pathlib import Path

from PIL import Image

from video_agent.adapters.rendering.frame_extractor import FrameExtractor
from video_agent.validation.preview_quality import PreviewQualityValidator
from video_agent.validation.rule_validation import RuleValidator



def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)



def test_frame_extractor_outputs_preview_images(tmp_path: Path) -> None:
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"normal-video")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n"
        "printf 'frame2' > \"$(dirname \"$6\")/frame_002.png\"\n",
    )

    frames = FrameExtractor(command=str(fake_ffmpeg)).extract(video_path, tmp_path / "previews")
    assert len(frames) >= 1
    assert frames[0].suffix == ".png"



def test_rule_validator_detects_black_video(tmp_path: Path) -> None:
    black_video_path = tmp_path / "black_video.mp4"
    black_video_path.write_bytes(b"black")
    report = RuleValidator().validate(black_video_path)
    assert report.passed is False
    assert any(issue.code == "black_frames" for issue in report.issues)


def test_preview_quality_validator_detects_static_previews(tmp_path: Path) -> None:
    frame_a = tmp_path / "frame_001.png"
    frame_b = tmp_path / "frame_002.png"
    Image.new("RGB", (320, 180), (180, 180, 180)).save(frame_a)
    Image.new("RGB", (320, 180), (180, 180, 180)).save(frame_b)

    report = PreviewQualityValidator().validate([frame_a, frame_b], profile={"check_static_previews": True})

    assert any(issue.code == "static_previews" for issue in report.issues)
