from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any

from video_agent.application.outcome_signals import item_delivery_passed, item_quality_passed


def build_eval_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    completed = sum(1 for item in items if item_quality_passed(item))
    delivered = sum(1 for item in items if item_delivery_passed(item))
    failed = sum(1 for item in items if item.get("status") == "failed")
    durations = [float(item.get("duration_seconds", 0.0)) for item in items]
    failure_codes = Counter(
        code
        for item in items
        if not item_quality_passed(item)
        for code in item.get("issue_codes", [])
    )
    report = {
        "completed_count": completed,
        "quality_pass_count": completed,
        "delivery_count": delivered,
        "failed_count": failed,
        "success_rate": (completed / total) if total else 0.0,
        "delivery_rate": (delivered / total) if total else 0.0,
        "failure_codes": dict(failure_codes),
        "median_duration_seconds": median(durations) if durations else 0.0,
    }
    agent_ids = {str(item.get("agent_id")) for item in items if item.get("agent_id")}
    if len(agent_ids) == 1:
        agent_items = [item for item in items if item.get("agent_id")]
        quality_scores = [float(item.get("quality_score", 0.0)) for item in agent_items if item.get("quality_score") is not None]
        issue_counter = Counter(code for item in agent_items for code in item.get("issue_codes", []))
        active_profile_digest = next(
            (
                item.get("profile_digest")
                for item in agent_items
                if item_quality_passed(item) and item.get("profile_digest")
            ),
            next((item.get("profile_digest") for item in agent_items if item.get("profile_digest")), None),
        )
        report["agent"] = {
            "agent_id": next(iter(agent_ids)),
            "pass_rate": (sum(1 for item in agent_items if item_quality_passed(item)) / len(agent_items))
            if agent_items
            else 0.0,
            "median_quality_score": median(quality_scores) if quality_scores else 0.0,
            "top_issue_codes": [code for code, _count in issue_counter.most_common(5)],
            "active_profile_digest": active_profile_digest,
        }
    return report


def _read_quality_pass_rate(report: dict[str, Any]) -> float:
    quality = report.get("quality")
    if isinstance(quality, dict):
        value = quality.get("pass_rate")
        if isinstance(value, (int, float)):
            return float(value)
    value = report.get("success_rate", 0.0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _read_delivery_rate(report: dict[str, Any]) -> float:
    value = report.get("delivery_rate")
    if isinstance(value, (int, float)):
        return float(value)
    return _read_quality_pass_rate(report)



def render_eval_report_markdown(summary: dict[str, Any]) -> str:
    report = summary["report"]
    lines = [
        "# Evaluation Summary",
        "",
        f"- Suite: `{summary['suite_id']}`",
        f"- Run ID: `{summary['run_id']}`",
        f"- Provider: `{summary['provider']}`",
        f"- Total Cases: {summary['total_cases']}",
        f"- Quality Pass Rate: {_read_quality_pass_rate(report):.2%}",
        f"- Delivery Rate: {_read_delivery_rate(report):.2%}",
        f"- Median Duration (s): {report['median_duration_seconds']}",
        "",
        "## Failures",
    ]
    if report["failure_codes"]:
        for code, count in sorted(report["failure_codes"].items()):
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("- None")
    repair_report = report.get("repair")
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
    quality_report = report.get("quality")
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
    live_report = report.get("live")
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
    agent_report = report.get("agent")
    if agent_report:
        lines.extend(
            [
                "",
                "## Agent Slice",
                f"- Agent ID: `{agent_report['agent_id']}`",
                f"- Quality Pass Rate: {agent_report['pass_rate']:.2%}",
                f"- Median Quality Score: {agent_report['median_quality_score']}",
                f"- Active Profile Digest: `{agent_report['active_profile_digest']}`",
            ]
        )
        top_issue_codes = agent_report.get("top_issue_codes", [])
        lines.append(f"- Top Issue Codes: {', '.join(top_issue_codes) if top_issue_codes else 'none'}")
    return "\n".join(lines) + "\n"
