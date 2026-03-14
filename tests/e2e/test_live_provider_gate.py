import json
import subprocess
import sys
from pathlib import Path


def test_live_provider_gate_fails_on_formula_regression(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "report": {
                    "live": {
                        "case_count": 4,
                        "pass_rate": 0.75,
                        "formula_pass_rate": 0.0,
                        "risk_domain_failure_counts": {"formula": 2, "camera": 0},
                    }
                }
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/live_provider_gate.py",
            "--summary",
            str(summary),
            "--min-live-pass-rate",
            "0.75",
            "--min-formula-pass-rate",
            "0.5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("formula_pass_rate" in reason for reason in payload["reasons"])


def test_live_provider_gate_detects_baseline_regression(tmp_path: Path) -> None:
    current = tmp_path / "current.json"
    baseline = tmp_path / "baseline.json"
    current.write_text(
        json.dumps(
            {
                "report": {
                    "live": {
                        "case_count": 4,
                        "pass_rate": 1.0,
                        "formula_pass_rate": 1.0,
                        "risk_domain_failure_counts": {"formula": 1, "camera": 1},
                    }
                }
            }
        )
    )
    baseline.write_text(
        json.dumps(
            {
                "report": {
                    "live": {
                        "risk_domain_failure_counts": {"formula": 0, "camera": 1}
                    }
                }
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/live_provider_gate.py",
            "--summary",
            str(current),
            "--baseline-summary",
            str(baseline),
            "--max-risk-regression",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert any("risk_domain formula regressed" in reason for reason in payload["reasons"])
