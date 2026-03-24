from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError
from video_agent.server.http_api import create_http_api
from video_agent.server.main import build_settings
from video_agent.version import get_release_metadata


def build_api_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--no-embedded-worker", action="store_true")
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim API {metadata['version']} ({metadata['channel']})")
    return parser


def main() -> None:
    parser = build_api_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir, run_embedded_worker=not args.no_embedded_worker)
    try:
        app = create_http_api(settings)
    except DatabaseBootstrapRequiredError as exc:
        raise SystemExit(str(exc)) from exc
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
