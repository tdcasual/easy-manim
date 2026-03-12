import json
import os
import subprocess
import sys
from pathlib import Path


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)


def _doctor_env(
    tmp_path: Path,
    *,
    latex_command: str,
    dvisvgm_command: str,
) -> dict[str, str]:
    fake_manim = tmp_path / "fake_manim.sh"
    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    _write_executable(fake_manim)
    _write_executable(fake_ffmpeg)
    _write_executable(fake_ffprobe)
    env = os.environ.copy()
    env.update(
        {
            "EASY_MANIM_MANIM_COMMAND": str(fake_manim),
            "EASY_MANIM_FFMPEG_COMMAND": str(fake_ffmpeg),
            "EASY_MANIM_FFPROBE_COMMAND": str(fake_ffprobe),
            "EASY_MANIM_LATEX_COMMAND": latex_command,
            "EASY_MANIM_DVISVGM_COMMAND": dvisvgm_command,
        }
    )
    return env


def test_doctor_cli_returns_json_summary(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.doctor.main", "--data-dir", str(data_dir), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert "checks" in payload
    assert "storage" in payload
    assert completed.returncode in {0, 1}


def test_doctor_cli_can_require_latex_support(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    missing = subprocess.run(
        [sys.executable, "-m", "video_agent.doctor.main", "--data-dir", str(data_dir), "--json", "--require-latex"],
        capture_output=True,
        text=True,
        check=False,
        env=_doctor_env(
            tmp_path,
            latex_command="missing-latex",
            dvisvgm_command="missing-dvisvgm",
        ),
    )

    missing_payload = json.loads(missing.stdout)

    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_executable(fake_latex)
    _write_executable(fake_dvisvgm)
    ready = subprocess.run(
        [sys.executable, "-m", "video_agent.doctor.main", "--data-dir", str(data_dir), "--json", "--require-latex"],
        capture_output=True,
        text=True,
        check=False,
        env=_doctor_env(
            tmp_path,
            latex_command=str(fake_latex),
            dvisvgm_command=str(fake_dvisvgm),
        ),
    )

    ready_payload = json.loads(ready.stdout)

    assert missing_payload["features"]["mathtex"]["available"] is False
    assert ready_payload["features"]["mathtex"]["available"] is True
    assert missing.returncode == 1
    assert ready.returncode == 0
