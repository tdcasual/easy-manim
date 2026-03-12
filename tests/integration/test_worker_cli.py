import subprocess



def test_worker_cli_help() -> None:
    completed = subprocess.run(
        ["python", "-m", "video_agent.worker.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--data-dir" in completed.stdout



def test_server_cli_can_disable_embedded_worker() -> None:
    completed = subprocess.run(
        ["python", "-m", "video_agent.server.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--no-embedded-worker" in completed.stdout
