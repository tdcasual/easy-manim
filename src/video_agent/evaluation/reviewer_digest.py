from __future__ import annotations

from typing import Any


def render_reviewer_digest(summary: dict[str, Any]) -> str:
    lines = [
        "# Reviewer Digest",
        "",
        f"- Run ID: `{summary['run_id']}`",
        "",
        "## Review First",
    ]
    items = sorted(
        summary.get("items", []),
        key=lambda item: (
            not item.get("manual_review_required", False),
            item.get("status") == "completed",
            item.get("case_id", ""),
        ),
    )
    review_first = False
    for item in items:
        if not item.get("manual_review_required") and item.get("status") == "completed":
            continue
        review_first = True
        lines.append(
            "- `{case_id}` (`{task_id}`): status={status}, risk_domains={risk_domains}, "
            "review_focus={review_focus}, issue_codes={issue_codes}, quality_issue_codes={quality_issue_codes}".format(
                case_id=item["case_id"],
                task_id=item["task_id"],
                status=item["status"],
                risk_domains=",".join(item.get("risk_domains", [])) or "none",
                review_focus=",".join(item.get("review_focus", [])) or "none",
                issue_codes=",".join(item.get("issue_codes", [])) or "none",
                quality_issue_codes=",".join(item.get("quality_issue_codes", [])) or "none",
            )
        )
    if not review_first:
        lines.append("- No priority review items")
    return "\n".join(lines) + "\n"
