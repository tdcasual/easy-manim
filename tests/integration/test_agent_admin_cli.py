import json
import os
import subprocess
import sys
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore


def test_agent_admin_cli_can_create_profile_and_issue_token(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")

    created = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.agent_admin.main",
            "--data-dir",
            str(data_dir),
            "create-profile",
            "--agent-id",
            "agent-a",
            "--name",
            "Agent A",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert created.returncode == 0

    issued = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.agent_admin.main",
            "--data-dir",
            str(data_dir),
            "issue-token",
            "--agent-id",
            "agent-a",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    payload = json.loads(issued.stdout)

    assert issued.returncode == 0
    assert payload["agent_id"] == "agent-a"
    assert payload["agent_token"]

    store = SQLiteTaskStore(data_dir / "video_agent.db")
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    assert store.get_agent_profile("agent-a") is not None
    assert store.get_agent_token(hash_agent_token(payload["agent_token"])) is not None
