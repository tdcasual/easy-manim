from __future__ import annotations

from collections import Counter
from typing import Any


def build_live_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    live_items = [item for item in items if "real-provider" in (item.get("tags") or [])]
    domain_counts = Counter(domain for item in live_items for domain in item.get("risk_domains", []))
    domain_failures = Counter(
        domain
        for item in live_items
        if item.get("status") != "completed"
        for domain in item.get("risk_domains", [])
    )
    formula_items = [item for item in live_items if "formula" in (item.get("risk_domains") or [])]
    failed_cases = [item.get("case_id") for item in live_items if item.get("status") != "completed"]
    total = len(live_items)
    completed = sum(1 for item in live_items if item.get("status") == "completed")
    formula_completed = sum(1 for item in formula_items if item.get("status") == "completed")
    return {
        "case_count": total,
        "pass_rate": (completed / total) if total else 0.0,
        "risk_domain_counts": dict(domain_counts),
        "risk_domain_failure_counts": dict(domain_failures),
        "formula_pass_rate": (formula_completed / len(formula_items)) if formula_items else 0.0,
        "top_failing_cases": [case_id for case_id in failed_cases[:5] if isinstance(case_id, str)],
    }
