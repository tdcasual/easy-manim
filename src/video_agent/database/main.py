from __future__ import annotations

import argparse
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.server.main import build_settings
from video_agent.version import get_release_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap and migrate the easy-manim SQLite database")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--json", action="store_true")
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim {metadata['version']} ({metadata['channel']})")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir)
    report = SQLiteBootstrapper(settings.database_path).bootstrap()
    if args.json:
        print(report.as_json())
        return
    if report.already_bootstrapped:
        print(f"database already bootstrapped at {report.database_path}")
        return
    print(f"applied migrations to {report.database_path}: {', '.join(report.applied_migration_ids)}")


if __name__ == "__main__":
    main()
