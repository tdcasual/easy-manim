from pathlib import Path
import subprocess
import sys
import tomllib


def test_db_bootstrap_entrypoint_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.database.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--data-dir" in completed.stdout


def test_db_bootstrap_script_is_declared_in_pyproject() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    assert pyproject["project"]["scripts"]["easy-manim-db-bootstrap"] == "video_agent.database.main:main"


def test_db_bootstrap_module_does_not_import_fastmcp_runtime() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import builtins\n"
                "real_import = builtins.__import__\n"
                "def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):\n"
                "    if name == 'video_agent.server.fastmcp_server' or name.startswith('video_agent.server.fastmcp_server.'):\n"
                "        raise RuntimeError('unexpected fastmcp import')\n"
                "    return real_import(name, globals, locals, fromlist, level)\n"
                "builtins.__import__ = guarded_import\n"
                "import video_agent.database.main as module\n"
                "module.build_parser()\n"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


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
