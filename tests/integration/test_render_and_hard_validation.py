import json
from pathlib import Path

from video_agent.adapters.rendering.manim_runner import ManimRunner
from video_agent.validation.hard_validation import HardValidator


FAKE_SCRIPT = "from manim import Scene\n\nclass Demo(Scene):\n    def construct(self):\n        pass\n"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)



def test_rendered_video_passes_hard_validation(tmp_path: Path) -> None:
    script_path = tmp_path / "scene.py"
    script_path.write_text(FAKE_SCRIPT)
    output_dir = tmp_path / "out"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'fake-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "printf 'render ok\\n'\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(
        fake_ffprobe,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-v\" ]; then exit 31; fi\n"
        f"printf '%s' '{probe_json}'\n",
    )

    render_result = ManimRunner(command=str(fake_manim)).render(script_path, output_dir)
    report = HardValidator(command=str(fake_ffprobe)).validate(render_result.video_path)

    assert render_result.video_path.exists()
    assert render_result.video_path.name == "final_video.mp4"
    assert report.passed is True
    assert report.video_metadata.width == 1280
    assert report.video_metadata.duration_seconds == 2.5


def test_manim_runner_passes_explicit_environment_to_subprocess(tmp_path: Path) -> None:
    script_path = tmp_path / "scene.py"
    script_path.write_text(FAKE_SCRIPT)
    output_dir = tmp_path / "out"

    fake_manim = tmp_path / "fake_manim_env.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$TEXMFCNF\" != \"/expected/path\" ]; then exit 41; fi\n"
        "printf '%s' \"$TEXMFCNF\" > \"$5/env-captured.txt\"\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'fake-video' > \"$5/videos/$script_name/480p15/$7\"\n",
    )

    render_result = ManimRunner(command=str(fake_manim)).render(
        script_path,
        output_dir,
        timeout_seconds=30,
        env={"TEXMFCNF": "/expected/path"},
    )

    assert render_result.exit_code == 0
    assert (output_dir / "env-captured.txt").read_text() == "/expected/path"
