from scripts.release_candidate_gate import evaluate_gate_result


def test_evaluate_gate_result_fails_when_pass_rate_is_too_low() -> None:
    result = evaluate_gate_result(
        {
            "eval": {"success_rate": 0.4},
            "smoke": {"status": "passed"},
            "tests": {"status": "passed"},
        },
        min_pass_rate=0.8,
    )

    assert result["ok"] is False
    assert "success_rate" in result["reasons"][0]


import subprocess
import sys


def test_release_candidate_gate_script_help_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/release_candidate_gate.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--min-pass-rate" in completed.stdout
