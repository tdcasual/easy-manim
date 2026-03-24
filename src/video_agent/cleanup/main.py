from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError
from video_agent.application.cleanup_service import CleanupService
from video_agent.server.app import create_app_context
from video_agent.server.main import build_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean retained easy-manim task data")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--older-than-hours", type=float, required=True)
    parser.add_argument("--status", action="append", default=[])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = build_settings(args.data_dir)
    try:
        context = create_app_context(settings)
    except DatabaseBootstrapRequiredError as exc:
        raise SystemExit(str(exc)) from exc
    service = CleanupService(store=context.store, artifact_store=context.artifact_store)
    older_than = datetime.now(timezone.utc) - timedelta(hours=args.older_than_hours)
    statuses = args.status or ["completed", "failed", "cancelled"]
    candidates = service.find_candidates(statuses=statuses, older_than_iso=older_than.isoformat(), limit=args.limit)

    if args.dry_run:
        payload = {
            "dry_run": True,
            "count": len(candidates),
            "items": [candidate.__dict__ for candidate in candidates],
        }
        if args.json:
            print(json.dumps(payload))
        else:
            for candidate in candidates:
                print(f"{candidate.task_id} {candidate.status} {candidate.updated_at}")
        raise SystemExit(0)

    if not args.confirm:
        print("Refusing destructive cleanup without --confirm", file=sys.stderr)
        raise SystemExit(2)

    summary = service.delete_candidates(candidates)
    payload = {
        "dry_run": False,
        "deleted_count": summary.deleted_count,
        "items": [candidate.__dict__ for candidate in summary.candidates],
    }
    if args.json:
        print(json.dumps(payload))
    else:
        print(f"deleted {summary.deleted_count} tasks")


if __name__ == "__main__":
    main()
