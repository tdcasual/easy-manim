from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper



def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]



def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]



def write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)



def build_fake_commands(tmp_path: Path) -> dict[str, Path]:
    fake_manim = tmp_path / "custom_manim.sh"
    write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n",
    )

    fake_ffprobe = tmp_path / "custom_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    write_executable(
        fake_ffprobe,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-v\" ]; then exit 31; fi\n"
        f"printf '%s' '{probe_json}'\n",
    )

    fake_ffmpeg = tmp_path / "custom_ffmpeg.sh"
    write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    return {"manim": fake_manim, "ffmpeg": fake_ffmpeg, "ffprobe": fake_ffprobe}



def wait_for_server(port: int, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise AssertionError(f"server on port {port} did not start in time")



def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


async def run_client_flow(url: str) -> dict[str, object]:
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(url) as streams:
        read_stream, write_stream, _session_id = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            created = await session.call_tool(
                "create_video_task",
                {"prompt": "draw a blue circle", "idempotency_key": "http-e2e"},
            )
            payload = created.structuredContent or {}
            task_id = payload["task_id"]

            snapshot: dict[str, object] = {}
            for _ in range(40):
                polled = await session.call_tool("get_video_task", {"task_id": task_id})
                snapshot = polled.structuredContent or {}
                if snapshot.get("status") in {"completed", "failed", "cancelled"}:
                    break
                await asyncio.sleep(0.2)

            result = await session.call_tool("get_video_result", {"task_id": task_id})
            return {
                "task_id": task_id,
                "snapshot": snapshot,
                "result": result.structuredContent or {},
            }



def run_beta_smoke(tmp_path: Path) -> dict[str, object]:
    data_dir = tmp_path / "data"
    port = pick_free_port()
    commands = build_fake_commands(tmp_path)
    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()

    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    env["EASY_MANIM_MANIM_COMMAND"] = str(commands["manim"])
    env["EASY_MANIM_FFMPEG_COMMAND"] = str(commands["ffmpeg"])
    env["EASY_MANIM_FFPROBE_COMMAND"] = str(commands["ffprobe"])

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "video_agent.server.main",
            "--transport",
            "streamable-http",
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
        return asyncio.run(run_client_flow(f"http://127.0.0.1:{port}/mcp"))
    finally:
        stop_process(worker)
        stop_process(server)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim beta smoke flow")
    parser.add_argument("--mode", choices=["local", "ci"], default="local")
    return parser



def main() -> None:
    build_parser().parse_args()
    with tempfile.TemporaryDirectory(prefix="easy-manim-beta-smoke-") as tmp_dir:
        summary = run_beta_smoke(Path(tmp_dir))
    print(json.dumps(summary))
    if summary["snapshot"].get("status") != "completed":
        raise SystemExit(1)
    if summary["result"].get("ready") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
