from __future__ import annotations

import argparse
import time
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError
from video_agent.server.app import create_app_context
from video_agent.server.main import build_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim standalone worker")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--poll-interval", type=float, default=None)
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--once", action="store_true")
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir, run_embedded_worker=False)
    if args.worker_id:
        settings.worker_id = args.worker_id
    try:
        app_context = create_app_context(settings)
    except DatabaseBootstrapRequiredError as exc:
        raise SystemExit(str(exc)) from exc
    poll_interval = args.poll_interval if args.poll_interval is not None else settings.worker_poll_interval_seconds

    if args.once:
        app_context.worker.run_once()
        return

    while True:
        processed = app_context.worker.run_once()
        if processed == 0:
            time.sleep(poll_interval)
        else:
            time.sleep(0)


if __name__ == "__main__":
    main()
