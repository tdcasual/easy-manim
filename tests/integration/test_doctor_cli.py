import json
import os
import subprocess
import sys
from pathlib import Path


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)


def _write_latex_success(path: Path) -> None:
    path.write_text("#!/bin/sh\nprintf 'dvi' > smoke.dvi\n")
    path.chmod(0o755)


def _write_dvisvgm_success(path: Path) -> None:
    path.write_text("#!/bin/sh\nprintf 'svg' > smoke.svg\n")
    path.chmod(0o755)


def _write_dvisvgm_failure(path: Path) -> None:
    path.write_text("#!/bin/sh\nprintf 'dvisvgm smoke failed' >&2\nexit 9\n")
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
    _write_latex_success(fake_latex)
    _write_dvisvgm_success(fake_dvisvgm)
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
    assert ready_payload["features"]["mathtex"]["checked"] is True
    assert ready_payload["features"]["mathtex"]["smoke_error"] is None
    assert missing.returncode == 1
    assert ready.returncode == 0


def test_doctor_cli_fails_when_latex_commands_exist_but_smoke_check_fails(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_latex_success(fake_latex)
    _write_dvisvgm_failure(fake_dvisvgm)

    completed = subprocess.run(
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

    payload = json.loads(completed.stdout)

    assert payload["checks"]["latex"]["available"] is True
    assert payload["checks"]["dvisvgm"]["available"] is True
    assert payload["features"]["mathtex"]["available"] is False
    assert payload["features"]["mathtex"]["checked"] is True
    assert "dvisvgm smoke failed" in payload["features"]["mathtex"]["smoke_error"].lower()
    assert completed.returncode == 1
