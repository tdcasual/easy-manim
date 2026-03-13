from __future__ import annotations

from collections import Counter
from typing import Any


def build_repair_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    repair_items = [item for item in items if "repair" in (item.get("tags") or [])]
    attempted = [item for item in repair_items if item.get("repair_attempted")]
    successes = [item for item in repair_items if item.get("repair_success")]
    failure_codes = Counter(
        code
        for item in repair_items
        if not item.get("repair_success")
        for code in item.get("issue_codes", [])
    )
    average_children = (
        sum(int(item.get("repair_children", 0)) for item in attempted) / len(attempted) if attempted else 0.0
    )
    case_count = len(repair_items)
    return {
        "case_count": case_count,
        "attempted_count": len(attempted),
        "repair_attempt_rate": (len(attempted) / case_count) if case_count else 0.0,
        "success_count": len(successes),
        "repair_success_rate": (len(successes) / case_count) if case_count else 0.0,
        "average_children_per_repaired_root": average_children,
        "failure_codes_after_repair": dict(failure_codes),
    }
