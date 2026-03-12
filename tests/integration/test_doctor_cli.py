import json
import subprocess
import sys
from pathlib import Path


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
