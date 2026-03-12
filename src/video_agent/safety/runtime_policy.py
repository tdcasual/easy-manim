from __future__ import annotations

from pathlib import Path


class RuntimePolicy:
    def __init__(self, work_root: Path, render_timeout_seconds: int = 300) -> None:
        self.work_root = Path(work_root).resolve()
        self.render_timeout_seconds = render_timeout_seconds

    def is_allowed_write(self, path: Path) -> bool:
        target = Path(path).resolve()
        try:
            target.relative_to(self.work_root)
            return True
        except ValueError:
            return False
