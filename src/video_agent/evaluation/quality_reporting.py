from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any


def build_quality_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    quality_items = [item for item in items if "quality" in (item.get("tags") or [])]
    scores = [float(item.get("quality_score", 0.0)) for item in quality_items]
    failures = Counter(
        code
        for item in quality_items
        for code in item.get("quality_issue_codes", [])
    )
    passed = sum(1 for item in quality_items if item.get("status") == "completed")
    total = len(quality_items)
    return {
        "case_count": total,
        "pass_rate": (passed / total) if total else 0.0,
        "median_quality_score": median(scores) if scores else 0.0,
        "quality_issue_codes": dict(failures),
    }
