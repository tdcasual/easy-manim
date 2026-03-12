import subprocess



def test_mcp_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-mcp", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "--transport" in completed.stdout



def test_worker_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-worker", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "--data-dir" in completed.stdout



def test_doctor_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-doctor", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "--strict-provider" in completed.stdout



def test_cleanup_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-cleanup", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "--older-than-hours" in completed.stdout



def test_export_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-export-task", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "--task-id" in completed.stdout


def test_mcp_entrypoint_version() -> None:
    completed = subprocess.run(["easy-manim-mcp", "--version"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "easy-manim" in completed.stdout


def test_doctor_entrypoint_version() -> None:
    completed = subprocess.run(["easy-manim-doctor", "--version"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "easy-manim" in completed.stdout
