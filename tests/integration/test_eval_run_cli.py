import json
import os
import subprocess
import sys
from pathlib import Path



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



def test_eval_run_cli_writes_summary_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    commands = _build_fake_commands(tmp_path)
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])

    completed = subprocess.run(
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

    payload = json.loads(completed.stdout)
    assert payload["suite_id"] == "beta-prompt-suite"
    assert payload["total_cases"] >= 1
    assert (data_dir / "evals" / payload["run_id"] / "summary.json").exists()
    assert completed.returncode == 0


def test_eval_run_cli_reports_repair_metrics(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    commands = _build_fake_commands(tmp_path)
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])
    env["EASY_MANIM_AUTO_REPAIR_ENABLED"] = "true"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            "evals/beta_prompt_suite.json",
            "--include-tag",
            "repair",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    payload = json.loads(completed.stdout)

    assert payload["total_cases"] == 1
    assert payload["items"][0]["repair_attempted"] is True
    assert payload["items"][0]["repair_success"] is True
    assert payload["report"]["repair"]["case_count"] == 1
    assert payload["report"]["repair"]["repair_attempt_rate"] == 1.0
    assert payload["report"]["repair"]["repair_success_rate"] == 1.0
    assert completed.returncode == 0


def test_eval_run_cli_reports_quality_metrics(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    commands = _build_fake_commands(tmp_path)
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            "evals/beta_prompt_suite.json",
            "--include-tag",
            "quality",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    payload = json.loads(completed.stdout)

    assert payload["total_cases"] >= 1
    assert payload["report"]["quality"]["case_count"] >= 1
    assert "median_quality_score" in payload["report"]["quality"]
    assert payload["report"]["live"]["case_count"] >= 1
    assert "risk_domain_counts" in payload["report"]["live"]
    assert "formula_pass_rate" in payload["report"]["live"]
    assert completed.returncode == 0


def test_eval_run_cli_can_require_all_tags(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "tag-intersection-demo",
                "cases": [
                    {"case_id": "quality-only", "prompt": "draw a circle", "tags": ["quality"]},
                    {"case_id": "provider-only", "prompt": "draw a square", "tags": ["real-provider"]},
                    {"case_id": "shared", "prompt": "show the quadratic formula and focus on the discriminant", "tags": ["real-provider", "quality"]},
                ],
            }
        )
    )
    commands = _build_fake_commands(tmp_path)
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            str(suite_path),
            "--include-tag",
            "real-provider",
            "--include-tag",
            "quality",
            "--match-all-tags",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    payload = json.loads(completed.stdout)

    assert payload["total_cases"] == 1
    assert payload["items"][0]["case_id"] == "shared"
    assert completed.returncode == 0
