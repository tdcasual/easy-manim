from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_NON_QUALITY_COMPLETION_MODES = {"degraded", "emergency_fallback"}


def is_quality_passed(
    *,
    status: str,
    quality_gate_status: str | None = None,
    completion_mode: str | None = None,
) -> bool:
    if status != "completed":
        return False
    if completion_mode in _NON_QUALITY_COMPLETION_MODES:
        return False
    if quality_gate_status == "needs_revision":
        return False
    return True


def is_delivery_passed(*, status: str, delivery_status: str | None = None) -> bool:
    return delivery_status == "delivered" or status == "completed"


def item_quality_passed(item: Mapping[str, Any]) -> bool:
    if item.get("quality_passed") is not None:
        return bool(item.get("quality_passed"))
    return is_quality_passed(
        status=str(item.get("status") or ""),
        quality_gate_status=_optional_str(item.get("quality_gate_status")),
        completion_mode=_optional_str(item.get("completion_mode")),
    )


def item_delivery_passed(item: Mapping[str, Any]) -> bool:
    if item.get("delivery_passed") is not None:
        return bool(item.get("delivery_passed"))
    return is_delivery_passed(
        status=str(item.get("status") or ""),
        delivery_status=_optional_str(item.get("delivery_status")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
