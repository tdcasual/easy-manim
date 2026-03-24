import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)



def _build_fake_commands(tmp_path: Path) -> dict[str, Path]:
    fake_manim = tmp_path / "custom_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n",
    )

    fake_ffprobe = tmp_path / "custom_ffprobe.sh"
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

    fake_ffmpeg = tmp_path / "custom_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    return {"manim": fake_manim, "ffmpeg": fake_ffmpeg, "ffprobe": fake_ffprobe}



def test_qa_bundle_cli_exports_eval_bundle(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    commands = _build_fake_commands(tmp_path)
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])

    eval_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            "evals/beta_prompt_suite.json",
            "--include-tag",
            "smoke",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    run_id = json.loads(eval_run.stdout)["run_id"]
    bundle_path = tmp_path / "qa-bundle.zip"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.qa_bundle.main",
            "--data-dir",
            str(data_dir),
            "--run-id",
            run_id,
            "--output",
            str(bundle_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 0
    with zipfile.ZipFile(bundle_path) as bundle:
        names = bundle.namelist()
        assert "summary.json" in names
        assert "summary.md" in names
        assert "review_digest.md" in names
