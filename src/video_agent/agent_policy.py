from __future__ import annotations

DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES = [
    "render_failed",
    "generation_failed",
    "syntax_error",
    "missing_scene",
    "unsafe_transformmatchingtex_slice",
    "unsafe_bare_tex_selection",
    "unsafe_bare_tex_highlight",
    "black_frames",
    "frozen_tail",
    "encoding_error",
    "min_width_not_met",
    "min_height_not_met",
    "min_duration_not_met",
]

QUALITY_ISSUE_CODES = {
    "near_blank_preview",
    "static_previews",
    "black_frames",
    "frozen_tail",
    "encoding_error",
    "min_width_not_met",
    "min_height_not_met",
    "min_duration_not_met",
}
