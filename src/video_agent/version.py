from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version



def get_release_metadata() -> dict[str, str]:
    try:
        package_version = version("easy-manim")
    except PackageNotFoundError:
        package_version = "0.1.0"
    return {
        "version": package_version,
        "channel": os.getenv("EASY_MANIM_RELEASE_CHANNEL", "beta"),
    }
