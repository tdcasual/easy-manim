import subprocess
import sys


def test_worker_cli_requires_bootstrapped_database(tmp_path) -> None:
    data_dir = tmp_path / "data"
    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.worker.main", "--once", "--data-dir", str(data_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "easy-manim-db-bootstrap" in completed.stderr


def test_worker_cli_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.worker.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--data-dir" in completed.stdout


def test_server_cli_can_disable_embedded_worker() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.server.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--no-embedded-worker" in completed.stdout
