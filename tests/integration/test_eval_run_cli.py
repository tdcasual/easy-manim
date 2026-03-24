import json
import os
import subprocess
import sys
from pathlib import Path

from video_agent.agent_policy import QUALITY_ISSUE_CODES
from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile



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
        "if grep -q \"config.background_color = '#F7F4EA'\" \"$2\"; then\n"
        "  printf 'bright-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "else\n"
        "  printf 'dark-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "fi\n",
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
        f"#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
        f"\"{sys.executable}\" - \"$3\" \"$6\" <<'PY'\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "import sys\n"
        "\n"
        "video_path = Path(sys.argv[1])\n"
        "output_pattern = Path(sys.argv[2])\n"
        "output_dir = output_pattern.parent\n"
        "output_dir.mkdir(parents=True, exist_ok=True)\n"
        "video_marker = video_path.read_bytes()\n"
        "rgb = (247, 244, 234) if b'bright-video' in video_marker else (0, 0, 0)\n"
        "Image.new('RGB', (320, 180), rgb).save(output_dir / 'frame_001.png')\n"
        "PY\n",
    )

    return {"manim": fake_manim, "ffmpeg": fake_ffmpeg, "ffprobe": fake_ffprobe}


def _count_task_dirs(data_dir: Path) -> int:
    tasks_dir = data_dir / "tasks"
    if not tasks_dir.exists():
        return 0
    return sum(1 for path in tasks_dir.iterdir() if path.is_dir())


def _build_eval_env(tmp_path: Path) -> tuple[dict[str, Path], dict[str, str]]:
    commands = _build_fake_commands(tmp_path)
    SQLiteBootstrapper(tmp_path / "data" / "video_agent.db").bootstrap()
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])
    return commands, env



def test_eval_run_cli_writes_summary_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _, env = _build_eval_env(tmp_path)

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


def test_eval_run_cli_can_resume_existing_run(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "resume-demo",
                "cases": [
                    {"case_id": "resume-case", "prompt": "draw a blue circle", "tags": ["smoke"]},
                ],
            }
        )
    )
    _, env = _build_eval_env(tmp_path)

    first = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            str(suite_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    first_payload = json.loads(first.stdout)
    first_task_count = _count_task_dirs(data_dir)

    resumed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            str(suite_path),
            "--resume-run-id",
            first_payload["run_id"],
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    resumed_payload = json.loads(resumed.stdout)
    manifest_payload = json.loads((data_dir / "evals" / first_payload["run_id"] / "run_manifest.json").read_text())

    assert resumed_payload["run_id"] == first_payload["run_id"]
    assert resumed_payload["items"] == first_payload["items"]
    assert _count_task_dirs(data_dir) == first_task_count
    assert manifest_payload["cases"]["resume-case"]["status"] == "completed"
    assert manifest_payload["cases"]["resume-case"]["attempt_count"] == 1
    assert resumed.returncode == 0


def test_eval_run_cli_can_rerun_completed_case_when_requested(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "resume-demo",
                "cases": [
                    {"case_id": "resume-case", "prompt": "draw a blue circle", "tags": ["smoke"]},
                ],
            }
        )
    )
    _, env = _build_eval_env(tmp_path)

    first = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            str(suite_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    first_payload = json.loads(first.stdout)
    first_task_count = _count_task_dirs(data_dir)

    rerun = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            str(suite_path),
            "--resume-run-id",
            first_payload["run_id"],
            "--rerun-case",
            "resume-case",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    rerun_payload = json.loads(rerun.stdout)
    manifest_payload = json.loads((data_dir / "evals" / first_payload["run_id"] / "run_manifest.json").read_text())

    assert rerun_payload["run_id"] == first_payload["run_id"]
    assert _count_task_dirs(data_dir) == first_task_count + 1
    assert rerun_payload["items"][0]["root_task_id"] != first_payload["items"][0]["root_task_id"]
    assert manifest_payload["cases"]["resume-case"]["attempt_count"] == 2
    assert rerun.returncode == 0


def test_eval_run_cli_reports_repair_metrics(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _, env = _build_eval_env(tmp_path)
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


def test_eval_run_cli_repair_case_avoids_near_blank_preview(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _, env = _build_eval_env(tmp_path)
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

    assert payload["items"][0]["quality_issue_codes"] == []
    assert payload["items"][0]["status"] == "completed"
    assert completed.returncode == 0


def test_eval_run_cli_reports_quality_metrics(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _, env = _build_eval_env(tmp_path)

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
    assert set(payload["report"]["quality"]["quality_issue_codes"]).issubset(QUALITY_ISSUE_CODES)
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
    _, env = _build_eval_env(tmp_path)

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


def test_eval_run_can_target_agent_profile(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    store = SQLiteTaskStore(data_dir / "video_agent.db")
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Prefer clean explanatory pacing.",
            summary_digest="digest-memory-1",
        )
    )
    _, env = _build_eval_env(tmp_path)

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
            "--agent-id",
            "agent-a",
            "--memory-id",
            "mem-1",
            "--profile-patch-json",
            json.dumps({"style_hints": {"tone": "teaching"}}),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    payload = json.loads(completed.stdout)

    assert payload["report"]["agent"]["agent_id"] == "agent-a"
    assert payload["report"]["agent"]["active_profile_digest"]
    assert payload["items"][0]["agent_id"] == "agent-a"
    assert payload["items"][0]["memory_ids"] == ["mem-1"]
    assert payload["items"][0]["profile_digest"] == payload["report"]["agent"]["active_profile_digest"]
    assert completed.returncode == 0
