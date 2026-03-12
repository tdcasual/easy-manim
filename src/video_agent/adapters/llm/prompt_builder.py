from __future__ import annotations

from typing import Any, Optional



def build_generation_prompt(
    prompt: str,
    output_profile: dict[str, Any] | None = None,
    feedback: Optional[str] = None,
    style_hints: dict[str, Any] | None = None,
) -> str:
    lines = ["Generate a runnable Manim script.", f"User request: {prompt}"]
    if output_profile:
        lines.append(f"Output profile: {output_profile}")
    if style_hints:
        lines.append(f"Style hints: {style_hints}")
    if feedback:
        lines.append(f"Revision feedback: {feedback}")
    lines.append("Return only Python code.")
    return "\n".join(lines)
