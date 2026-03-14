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
    repair_report = summary["report"].get("repair")
    if repair_report:
        lines.extend(
            [
                "",
                "## Repair Slice",
                f"- Repair Cases: {repair_report['case_count']}",
                f"- Repair Attempt Rate: {repair_report['repair_attempt_rate']:.2%}",
                f"- Repair Success Rate: {repair_report['repair_success_rate']:.2%}",
                f"- Avg Children / Repaired Root: {repair_report['average_children_per_repaired_root']}",
            ]
        )
    quality_report = summary["report"].get("quality")
    if quality_report:
        lines.extend(
            [
                "",
                "## Quality Slice",
                f"- Quality Cases: {quality_report['case_count']}",
                f"- Quality Pass Rate: {quality_report['pass_rate']:.2%}",
                f"- Median Quality Score: {quality_report['median_quality_score']}",
            ]
        )
    live_report = summary["report"].get("live")
    if live_report:
        lines.extend(
            [
                "",
                "## Live Slice",
                f"- Live Cases: {live_report['case_count']}",
                f"- Live Pass Rate: {live_report['pass_rate']:.2%}",
                f"- Formula Pass Rate: {live_report['formula_pass_rate']:.2%}",
            ]
        )
        domain_failures = live_report.get("risk_domain_failure_counts", {})
        if domain_failures:
            lines.append("- Risk Domain Failures:")
            for domain, count in sorted(domain_failures.items()):
                lines.append(f"  - `{domain}`: {count}")
    return "\n".join(lines) + "\n"
