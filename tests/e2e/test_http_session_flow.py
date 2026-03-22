import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from scripts.beta_smoke import build_fake_commands, pick_free_port, repo_root, stop_process, wait_for_server


def test_http_session_flow_end_to_end(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    port = pick_free_port()
    commands = build_fake_commands(tmp_path)

    env = os.environ.copy()
    src_path = str(repo_root() / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_AUTH_MODE"] = "required"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])

    subprocess.run(
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
        cwd=repo_root(),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
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
        cwd=repo_root(),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    agent_token = json.loads(issued.stdout)["agent_token"]

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "video_agent.server.api_main",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--data-dir",
            str(data_dir),
            "--no-embedded-worker",
        ],
        cwd=repo_root(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    worker = subprocess.Popen(
        [sys.executable, "-m", "video_agent.worker.main", "--data-dir", str(data_dir)],
        cwd=repo_root(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_server(port)
        base_url = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            login = client.post("/api/sessions", json={"agent_token": agent_token})
            assert login.status_code == 200
            session_token = login.json()["session_token"]
            headers = {"Authorization": f"Bearer {session_token}"}

            whoami = client.get("/api/whoami", headers=headers)
            assert whoami.status_code == 200
            assert whoami.json()["agent_id"] == "agent-a"

            created = client.post("/api/tasks", json={"prompt": "draw a blue circle"}, headers=headers)
            assert created.status_code == 200
            task_id = created.json()["task_id"]

            snapshot = {}
            for _ in range(40):
                task_response = client.get(f"/api/tasks/{task_id}", headers=headers)
                assert task_response.status_code == 200
                snapshot = task_response.json()
                if snapshot["status"] in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(0.2)

            assert snapshot["status"] == "completed"

            result = client.get(f"/api/tasks/{task_id}/result", headers=headers)
            assert result.status_code == 200
            assert result.json()["ready"] is True

            memory = client.get("/api/memory/session", headers=headers)
            assert memory.status_code == 200
            assert memory.json()["entry_count"] >= 1

            summary = client.get("/api/memory/session/summary", headers=headers)
            assert summary.status_code == 200
            assert summary.json()["entry_count"] >= 1

            logout = client.delete("/api/sessions/current", headers=headers)
            assert logout.status_code == 200
            assert logout.json()["revoked"] is True

            revoked = client.get("/api/whoami", headers=headers)
            assert revoked.status_code == 401
    finally:
        stop_process(worker)
        stop_process(server)
