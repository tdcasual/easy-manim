from __future__ import annotations

from typing import Any


def build_targeted_repair_feedback(
    issue_code: str,
    failure_context: dict[str, Any],
    memory_context_summary: str | None = None,
) -> str:
    lines = [
        "Previous attempt failed.",
        "Targeted repair only.",
        "Preserve working code outside the failing region.",
        "Revise only the minimal failing region or behavior.",
        "Return a full updated Python script.",
        f"Failure code: {issue_code}.",
    ]
    if memory_context_summary:
        lines.append(f"Session memory context: {_condense(memory_context_summary)}.")

    if focus_summary := _focus_summary(failure_context):
        lines.append(f"Primary repair target: {focus_summary}.")
    if summary := failure_context.get("summary"):
        lines.append(f"Summary: {_condense(summary)}.")
    if failure_message := failure_context.get("failure_message"):
        lines.append(f"Failure message: {_condense(failure_message)}.")
    if stderr := failure_context.get("stderr"):
        lines.append(f"Render stderr: {_condense(stderr)}.")
    if provider_error := failure_context.get("provider_error"):
        lines.append(f"Provider error: {_condense(provider_error)}.")
    missing_checks = failure_context.get("missing_checks") or []
    if missing_checks:
        lines.append(f"Missing runtime checks: {', '.join(str(item) for item in missing_checks)}.")
    preview_issue_codes = failure_context.get("preview_issue_codes") or []
    for instruction in _preview_guidance(preview_issue_codes):
        lines.append(instruction)

    for item in (failure_context.get("semantic_diagnostics") or [])[:3]:
        lines.append(_format_semantic_diagnostic(item))

    if script_resource := failure_context.get("current_script_resource"):
        lines.append(f"Use {script_resource} as the starting point for the revision.")

    return " ".join(lines)


def _focus_summary(failure_context: dict[str, Any]) -> str | None:
    diagnostics = failure_context.get("semantic_diagnostics") or []
    if diagnostics:
        first = diagnostics[0]
        call_name = first.get("call_name")
        line = first.get("line")
        code = first.get("code") or "semantic_issue"
        keywords = first.get("keywords") or []
        parts = [str(code)]
        if call_name:
            parts.append(f"on {call_name}")
        if line:
            parts.append(f"at line {line}")
        if keywords:
            parts.append(f"with keywords {', '.join(str(keyword) for keyword in keywords)}")
        return " ".join(parts)

    failure_message = failure_context.get("failure_message")
    if failure_message:
        return _condense(str(failure_message))
    return None


def _format_semantic_diagnostic(item: dict[str, Any]) -> str:
    code = item.get("code") or "unknown"
    line = item.get("line")
    call_name = item.get("call_name")
    keywords = item.get("keywords") or []
    parts = [f"Semantic diagnosis: {code}"]
    if call_name:
        parts.append(f"on {call_name}")
    if line:
        parts.append(f"at line {line}")
    if keywords:
        parts.append(f"with keywords {', '.join(str(keyword) for keyword in keywords)}")
    detail = " ".join(parts) + "."
    message = item.get("message")
    if message:
        detail = f"{detail} {_condense(str(message))}."
    return detail


def _condense(value: str, limit: int = 400) -> str:
    condensed = " ".join(str(value).split())
    if len(condensed) <= limit:
        return condensed
    return condensed[: limit - 3] + "..."


def _preview_guidance(preview_issue_codes: list[str]) -> list[str]:
    instructions: list[str] = []
    codes = set(preview_issue_codes)
    if "near_blank_preview" in codes:
        instructions.extend(
            [
                "Do not open on a blank or almost blank frame.",
                "Set the light background before scene construction begins, not midway through the animation.",
                "Make the first beat visibly populated with readable text, geometry, axes, or another clear focal object.",
            ]
        )
    if "near_blank_preview" in codes or "static_previews" in codes:
        instructions.extend(
            [
                "Add a clearly visible motion beat so the preview sequence is not effectively static.",
                (
                    "Within the first 2 seconds, change position, scale, or emphasis of an existing on-screen "
                    "object; do not rely on wait() alone."
                ),
                "Keep at least two visually distinct states across the preview frames.",
            ]
        )
    return instructions
