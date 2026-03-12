from pathlib import Path

from video_agent.adapters.rendering.frame_extractor import FrameExtractor
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
