from __future__ import annotations

import ast
import os
import subprocess
import time
from pathlib import Path

from pydantic import BaseModel


class RenderResult(BaseModel):
    video_path: Path
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float


class ManimRunner:
    def __init__(self, command: str = "manim", base_env: dict[str, str] | None = None) -> None:
        self.command = command
        self.base_env = dict(base_env or {})

    def render(
        self,
        script_path: Path,
        output_dir: Path,
        timeout_seconds: float | None = None,
        env: dict[str, str] | None = None,
    ) -> RenderResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        scene_name = self._extract_scene_name(Path(script_path))
        output_name = "final_video.mp4"
        start = time.monotonic()
        effective_env = None
        if self.base_env or env:
            effective_env = dict(os.environ)
            effective_env.update(self.base_env)
            effective_env.update(env or {})
        try:
            completed = subprocess.run(
                [
                    self.command,
                    "-ql",
                    str(script_path),
                    scene_name,
                    "--media_dir",
                    str(output_dir),
                    "-o",
                    output_name,
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
                env=effective_env,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "").strip()
            timeout_message = f"Render timed out after {timeout_seconds} seconds"
            stderr = f"{stderr}\n{timeout_message}".strip()
            exit_code = 124

        duration = time.monotonic() - start
        video_path = self._locate_output_video(output_dir, output_name)
        return RenderResult(
            video_path=video_path,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_seconds=duration,
        )

    def _extract_scene_name(self, script_path: Path) -> str:
        tree = ast.parse(script_path.read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if getattr(base, "id", None) == "Scene":
                        return node.name
        return script_path.stem

    def _locate_output_video(self, output_dir: Path, output_name: str) -> Path:
        direct_path = output_dir / output_name
        if direct_path.exists():
            return direct_path

        candidates = sorted(output_dir.rglob(output_name))
        if candidates:
            return candidates[0]
        return direct_path
