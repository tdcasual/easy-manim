from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Any

from scripts.beta_smoke import build_fake_commands, repo_root



ENTRYPOINT_MODULES = {
    "easy-manim-mcp": "video_agent.server.main",
    "easy-manim-worker": "video_agent.worker.main",
    "easy-manim-doctor": "video_agent.doctor.main",
    "easy-manim-cleanup": "video_agent.cleanup.main",
    "easy-manim-export-task": "video_agent.export.main",
    "easy-manim-eval-run": "video_agent.eval.main",
    "easy-manim-qa-bundle": "video_agent.qa_bundle.main",
}


def evaluate_gate_result(
    payload: dict[str, Any],
    min_pass_rate: float,
    min_repair_success_rate: float = 0.0,
) -> dict[str, Any]:
    reasons: list[str] = []

    if payload.get("doctor", {}).get("status") == "failed":
        reasons.append("doctor_status failed")
    if payload.get("tests", {}).get("status") != "passed":
        reasons.append("tests_status failed")
    if payload.get("smoke", {}).get("status") != "passed":
        reasons.append("smoke_status failed")

    success_rate = float(payload.get("eval", {}).get("success_rate", 0.0))
    if success_rate < min_pass_rate:
        reasons.append(f"success_rate {success_rate:.2f} below threshold {min_pass_rate:.2f}")

    repair_eval = payload.get("repair_eval", {})
    if repair_eval.get("status") != "passed":
        reasons.append("repair_eval_status failed")
    repair_case_count = int(repair_eval.get("case_count", 0) or 0)
    repair_success_rate = float(repair_eval.get("repair_success_rate", 0.0))
    if repair_case_count == 0:
        reasons.append("repair_eval_case_count 0")
    elif repair_success_rate < min_repair_success_rate:
        reasons.append(
            f"repair_success_rate {repair_success_rate:.2f} below threshold {min_repair_success_rate:.2f}"
        )

    return {"ok": not reasons, "reasons": reasons}



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim release candidate gate")
    parser.add_argument("--mode", choices=["local", "ci"], default="local")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--min-pass-rate", type=float, default=0.8)
    parser.add_argument("--min-repair-success-rate", type=float, default=0.8)
    return parser



def _run_command(command: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd, env=env)



def _status_for(result: subprocess.CompletedProcess[str]) -> str:
    return "passed" if result.returncode == 0 else "failed"



def _parse_json(stdout: str) -> dict[str, Any]:
    content = stdout.strip()
    return json.loads(content) if content else {}



def _build_env(mode: str, scratch_dir: Path) -> tuple[dict[str, str], Path]:
    env = os.environ.copy()
    data_dir = scratch_dir / "data" if mode == "ci" else Path(env.get("EASY_MANIM_DATA_DIR", scratch_dir / "data"))
    project_root = repo_root()
    env["PYTHONPATH"] = str(project_root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    _install_test_shims(scratch_dir, env)
    if mode == "ci":
        commands = build_fake_commands(scratch_dir)
        env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
        env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
        env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])
        env.setdefault("EASY_MANIM_RELEASE_CHANNEL", "rc")
        env.setdefault("EASY_MANIM_AUTO_REPAIR_ENABLED", "true")
    return env, data_dir


def _install_test_shims(scratch_dir: Path, env: dict[str, str]) -> None:
    bin_dir = scratch_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    python_shim = bin_dir / "python"
    python_shim.write_text(f"#!/bin/sh\nexec {sys.executable} \"$@\"\n")
    python_shim.chmod(0o755)

    for name, module in ENTRYPOINT_MODULES.items():
        target = bin_dir / name
        target.write_text(f"#!/bin/sh\nexec {sys.executable} -m {module} \"$@\"\n")
        target.chmod(0o755)

    env["PATH"] = str(bin_dir) + (os.pathsep + env["PATH"] if env.get("PATH") else "")



def run_release_candidate_gate(
    mode: str,
    data_dir: Path,
    min_pass_rate: float,
    min_repair_success_rate: float,
) -> dict[str, Any]:
    root = repo_root()
    if mode == "ci":
        scratch_parent = data_dir.parent if data_dir != Path("data") else None
    else:
        scratch_parent = data_dir.parent

    with tempfile.TemporaryDirectory(prefix="easy-manim-rc-gate-", dir=scratch_parent) as tmp_dir:
        scratch_dir = Path(tmp_dir)
        env, effective_data_dir = _build_env(mode, scratch_dir)
        if mode != "ci":
            effective_data_dir = data_dir

        doctor_result = _run_command(
            [sys.executable, "-m", "video_agent.doctor.main", "--data-dir", str(effective_data_dir), "--json"],
            env=env,
            cwd=root,
        )
        tests_result = _run_command([sys.executable, "-m", "pytest", "-q"], env=env, cwd=root)
        smoke_result = _run_command(
            [sys.executable, "scripts/beta_smoke.py", "--mode", "ci" if mode == "ci" else mode],
            env=env,
            cwd=root,
        )
        eval_result = _run_command(
            [
                sys.executable,
                "-m",
                "video_agent.eval.main",
                "--data-dir",
                str(effective_data_dir),
                "--suite",
                "evals/beta_prompt_suite.json",
                "--include-tag",
                "smoke",
                "--json",
            ],
            env=env,
            cwd=root,
        )
        repair_eval_result = _run_command(
            [
                sys.executable,
                "-m",
                "video_agent.eval.main",
                "--data-dir",
                str(effective_data_dir),
                "--suite",
                "evals/beta_prompt_suite.json",
                "--include-tag",
                "repair",
                "--json",
            ],
            env=env,
            cwd=root,
        )

        summary = {
            "doctor": {
                "status": _status_for(doctor_result),
                "returncode": doctor_result.returncode,
                "payload": _parse_json(doctor_result.stdout) if doctor_result.stdout.strip() else {},
            },
            "tests": {
                "status": _status_for(tests_result),
                "returncode": tests_result.returncode,
                "stdout": tests_result.stdout.strip(),
            },
            "smoke": {
                "status": _status_for(smoke_result),
                "returncode": smoke_result.returncode,
                "payload": _parse_json(smoke_result.stdout) if smoke_result.stdout.strip() else {},
            },
            "eval": {
                "status": _status_for(eval_result),
                "returncode": eval_result.returncode,
            },
            "repair_eval": {
                "status": _status_for(repair_eval_result),
                "returncode": repair_eval_result.returncode,
            },
        }

        if eval_result.stdout.strip():
            eval_payload = _parse_json(eval_result.stdout)
            summary["eval"].update(
                {
                    "run_id": eval_payload.get("run_id"),
                    "suite_id": eval_payload.get("suite_id"),
                    "total_cases": eval_payload.get("total_cases"),
                    "success_rate": eval_payload.get("report", {}).get("success_rate", 0.0),
                    "summary_json": str(effective_data_dir / "evals" / eval_payload.get("run_id", "") / "summary.json"),
                    "summary_md": str(effective_data_dir / "evals" / eval_payload.get("run_id", "") / "summary.md"),
                }
            )
        else:
            summary["eval"]["success_rate"] = 0.0

        if repair_eval_result.stdout.strip():
            repair_eval_payload = _parse_json(repair_eval_result.stdout)
            repair_report = repair_eval_payload.get("report", {}).get("repair", {})
            summary["repair_eval"].update(
                {
                    "run_id": repair_eval_payload.get("run_id"),
                    "suite_id": repair_eval_payload.get("suite_id"),
                    "case_count": repair_report.get("case_count", 0),
                    "repair_attempt_rate": repair_report.get("repair_attempt_rate", 0.0),
                    "repair_success_rate": repair_report.get("repair_success_rate", 0.0),
                    "summary_json": str(effective_data_dir / "evals" / repair_eval_payload.get("run_id", "") / "summary.json"),
                    "summary_md": str(effective_data_dir / "evals" / repair_eval_payload.get("run_id", "") / "summary.md"),
                }
            )
        else:
            summary["repair_eval"]["case_count"] = 0
            summary["repair_eval"]["repair_success_rate"] = 0.0

        summary.update(
            evaluate_gate_result(
                summary,
                min_pass_rate=min_pass_rate,
                min_repair_success_rate=min_repair_success_rate,
            )
        )
        return summary



def main() -> None:
    args = build_parser().parse_args()
    summary = run_release_candidate_gate(
        args.mode,
        args.data_dir,
        args.min_pass_rate,
        args.min_repair_success_rate,
    )
    print(json.dumps(summary))
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
