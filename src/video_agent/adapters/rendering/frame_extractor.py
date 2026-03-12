from __future__ import annotations

import subprocess
from pathlib import Path


class FrameExtractor:
    def __init__(self, command: str = "ffmpeg") -> None:
        self.command = command

    def extract(self, video_path: Path, output_dir: Path) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                self.command,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                "fps=1",
                str(output_dir / "frame_%03d.png"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return sorted(output_dir.glob("*.png"))
