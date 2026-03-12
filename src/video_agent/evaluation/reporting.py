from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any



def build_eval_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    completed = sum(1 for item in items if item.get("status") == "completed")
    failed = sum(1 for item in items if item.get("status") == "failed")
    durations = [float(item.get("duration_seconds", 0.0)) for item in items]
    failure_codes = Counter(
        code
        for item in items
        if item.get("status") != "completed"
        for code in item.get("issue_codes", [])
    )
    return {
        "completed_count": completed,
        "failed_count": failed,
        "success_rate": (completed / total) if total else 0.0,
        "failure_codes": dict(failure_codes),
        "median_duration_seconds": median(durations) if durations else 0.0,
    }



def render_eval_report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Summary",
        "",
        f"- Suite: `{summary['suite_id']}`",
        f"- Run ID: `{summary['run_id']}`",
        f"- Provider: `{summary['provider']}`",
        f"- Total Cases: {summary['total_cases']}",
        f"- Success Rate: {summary['report']['success_rate']:.2%}",
        f"- Median Duration (s): {summary['report']['median_duration_seconds']}",
        "",
        "## Failures",
    ]
    if summary["report"]["failure_codes"]:
        for code, count in sorted(summary["report"]["failure_codes"].items()):
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"
