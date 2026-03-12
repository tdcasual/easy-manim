from __future__ import annotations

import argparse
import os
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.fastmcp_server import create_mcp_server
from video_agent.version import get_release_metadata



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim MCP server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-embedded-worker", action="store_true")
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim {metadata['version']} ({metadata['channel']})")
    return parser



def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)



def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)



def build_settings(data_dir: Path, run_embedded_worker: bool = True) -> Settings:
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        eval_root=Path(os.getenv("EASY_MANIM_EVAL_ROOT", str(data_dir / "evals"))),
        manim_command=os.getenv("EASY_MANIM_MANIM_COMMAND", "manim"),
        latex_command=os.getenv("EASY_MANIM_LATEX_COMMAND", "latex"),
        dvisvgm_command=os.getenv("EASY_MANIM_DVISVGM_COMMAND", "dvisvgm"),
        ffmpeg_command=os.getenv("EASY_MANIM_FFMPEG_COMMAND", "ffmpeg"),
        ffprobe_command=os.getenv("EASY_MANIM_FFPROBE_COMMAND", "ffprobe"),
        release_channel=os.getenv("EASY_MANIM_RELEASE_CHANNEL", "beta"),
        default_poll_after_ms=_env_int("EASY_MANIM_DEFAULT_POLL_AFTER_MS", 2000),
        llm_provider=os.getenv("EASY_MANIM_LLM_PROVIDER", "stub"),
        llm_model=os.getenv("EASY_MANIM_LLM_MODEL", "stub-manim-v1"),
        llm_base_url=os.getenv("EASY_MANIM_LLM_BASE_URL"),
        llm_api_key=os.getenv("EASY_MANIM_LLM_API_KEY"),
        llm_timeout_seconds=_env_int("EASY_MANIM_LLM_TIMEOUT_SECONDS", 60),
        llm_max_retries=_env_int("EASY_MANIM_LLM_MAX_RETRIES", 2),
        run_embedded_worker=run_embedded_worker,
        worker_poll_interval_seconds=_env_float("EASY_MANIM_WORKER_POLL_INTERVAL_SECONDS", 0.2),
        worker_lease_seconds=_env_int("EASY_MANIM_WORKER_LEASE_SECONDS", 30),
        worker_recovery_grace_seconds=_env_int("EASY_MANIM_WORKER_RECOVERY_GRACE_SECONDS", 5),
        worker_stale_after_seconds=_env_int("EASY_MANIM_WORKER_STALE_AFTER_SECONDS", 30),
        max_queued_tasks=_env_int("EASY_MANIM_MAX_QUEUED_TASKS", 20),
        max_attempts_per_root_task=_env_int("EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK", 5),
    )



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir, run_embedded_worker=not args.no_embedded_worker)
    mcp = create_mcp_server(settings, host=args.host, port=args.port, debug=args.debug)
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
