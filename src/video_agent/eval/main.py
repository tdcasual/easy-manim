from __future__ import annotations

import argparse
import json
from pathlib import Path

from video_agent.application.eval_service import EvaluationService
from video_agent.server.app import create_app_context
from video_agent.server.main import build_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim evaluation suite")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--suite", required=True)
    parser.add_argument("--include-tag", action="append", default=[])
    parser.add_argument("--match-all-tags", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--json", action="store_true")
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir)
    context = create_app_context(settings)
    service = EvaluationService(context)
    summary = service.run_suite(
        suite_path=args.suite,
        include_tags=set(args.include_tag) or None,
        limit=args.limit,
        match_all_tags=args.match_all_tags,
    )
    payload = summary.model_dump(mode="json")
    if args.json:
        print(json.dumps(payload))
    else:
        repair_report = payload["report"].get("repair", {})
        repair_success_rate = repair_report.get("repair_success_rate", 0.0)
        quality_report = payload["report"].get("quality", {})
        quality_pass_rate = quality_report.get("pass_rate", 0.0)
        print(
            f"{payload['run_id']} {payload['suite_id']} {payload['total_cases']} "
            f"repair_success_rate={repair_success_rate:.2f} quality_pass_rate={quality_pass_rate:.2f}"
        )

if __name__ == "__main__":
    main()
