from __future__ import annotations

import argparse
import json
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError
from video_agent.application.delivery_canary_service import (
    DEFAULT_DELIVERY_CANARY_MODE,
    DEFAULT_DELIVERY_CANARY_PROMPT,
    DELIVERY_CANARY_MODES,
    DeliveryCanaryService,
)
from video_agent.server.app import create_app_context
from video_agent.server.main import build_settings
from video_agent.version import get_release_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local delivery canary for easy-manim")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--prompt", default=DEFAULT_DELIVERY_CANARY_PROMPT)
    parser.add_argument("--mode", choices=sorted(DELIVERY_CANARY_MODES), default=DEFAULT_DELIVERY_CANARY_MODE)
    parser.add_argument("--max-worker-iterations", type=int)
    parser.add_argument("--json", action="store_true")
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim {metadata['version']} ({metadata['channel']})")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir, run_embedded_worker=False)
    try:
        context = create_app_context(settings)
    except DatabaseBootstrapRequiredError as exc:
        raise SystemExit(str(exc)) from exc

    payload = DeliveryCanaryService(
        settings=context.settings,
        store=context.store,
        artifact_store=context.artifact_store,
        task_service=context.task_service,
        worker=context.worker,
    ).run(
        prompt=args.prompt,
        max_worker_iterations=args.max_worker_iterations,
        mode=args.mode,
    )
    if args.json:
        print(json.dumps(payload))
        return
    print(
        f"delivered={payload['delivered']} "
        f"task_id={payload['task_id']} "
        f"completion_mode={payload['completion_mode']} "
        f"run_duration_seconds={payload['run_duration_seconds']}"
    )


if __name__ == "__main__":
    main()
