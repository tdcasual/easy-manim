from __future__ import annotations

import re


_FENCED_BLOCK_PATTERN = re.compile(r"```[\w-]*\s*\r?\n(?P<code>[\s\S]*?)```", re.IGNORECASE)


def sanitize_script_text(content: str) -> str:
    text = content.strip()
    fenced_match = _FENCED_BLOCK_PATTERN.search(text)
    if fenced_match is not None:
        return fenced_match.group("code").strip()
    return text
