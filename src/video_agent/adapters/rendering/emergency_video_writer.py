from __future__ import annotations

import base64
import subprocess
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4


_EMBEDDED_MINIMAL_MP4_BASE64 = (
    "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"
)


class EmergencyVideoWriter:
    def __init__(
        self,
        command: str = "ffmpeg",
        validator: Callable[[Path], bool] | None = None,
    ) -> None:
        self.command = command
        self.validator = validator

    def write(self, output_path: Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_name(f".{target.stem}.{uuid4().hex}.tmp{target.suffix}")
        try:
            if not self._try_ffmpeg(staged):
                staged.write_bytes(base64.b64decode(_EMBEDDED_MINIMAL_MP4_BASE64))
            if self.validator is not None and not self.validator(staged):
                raise EmergencyVideoWriteError("invalid_emergency_video")
            staged.replace(target)
        finally:
            if staged.exists():
                staged.unlink()
        return target

    def _try_ffmpeg(self, output_path: Path) -> bool:
        try:
            completed = subprocess.run(
                [
                    self.command,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=1280x720:d=1",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        return completed.returncode == 0 and output_path.exists()


class EmergencyVideoWriteError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
