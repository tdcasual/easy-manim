import importlib.util
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore


def _load_cli_runner():
    module_path = Path(__file__).resolve().parents[1] / "support" / "cli_runner.py"
    spec = importlib.util.spec_from_file_location("tests_support_cli_runner", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Failed to load cli runner module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_repo_module_json = _load_cli_runner().run_repo_module_json


def test_agent_admin_cli_can_create_profile_and_issue_token(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    created = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(data_dir),
        "create-profile",
        "--agent-id",
        "agent-a",
        "--name",
        "Agent A",
    )
    assert created["agent_id"] == "agent-a"

    payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(data_dir),
        "issue-token",
        "--agent-id",
        "agent-a",
    )
    assert payload["agent_id"] == "agent-a"
    assert payload["agent_token"]

    store = SQLiteTaskStore(data_dir / "video_agent.db")
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    assert store.get_agent_profile("agent-a") is not None
    assert store.get_agent_token(hash_agent_token(payload["agent_token"])) is not None
