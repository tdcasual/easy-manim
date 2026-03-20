from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


def build_system_default_request_config(
    *,
    default_quality_preset: str,
    default_frame_rate: int | None,
    default_pixel_width: int | None,
    default_pixel_height: int | None,
) -> dict[str, Any]:
    output_profile: dict[str, Any] = {"quality_preset": default_quality_preset}
    if default_frame_rate is not None:
        output_profile["frame_rate"] = default_frame_rate
    if default_pixel_width is not None:
        output_profile["pixel_width"] = default_pixel_width
    if default_pixel_height is not None:
        output_profile["pixel_height"] = default_pixel_height
    return {"output_profile": output_profile}


def resolve_effective_request_config(
    *,
    system_defaults: dict[str, Any] | None = None,
    profile_json: dict[str, Any] | None = None,
    token_override_json: dict[str, Any] | None = None,
    request_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective: dict[str, Any] = {}
    for layer in (system_defaults, profile_json, token_override_json, request_overrides):
        effective = _deep_merge(effective, layer or {})
    return effective


def compute_profile_digest(config: dict[str, Any]) -> str:
    normalized = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
            continue
        merged[key] = deepcopy(value)
    return merged
