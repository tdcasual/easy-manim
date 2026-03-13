from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from pydantic import BaseModel


class RuntimeSmokeResult(BaseModel):
    checked: bool
    available: bool
    error: str | None = None


def run_mathtex_smoke(
    work_dir: Path,
    latex_command: str,
    dvisvgm_command: str,
    env: dict[str, str] | None = None,
    timeout_seconds: float = 20,
) -> RuntimeSmokeResult:
    target = Path(work_dir)
    target.mkdir(parents=True, exist_ok=True)

    tex_path = target / "smoke.tex"
    dvi_path = target / "smoke.dvi"
    svg_path = target / "smoke.svg"
    tex_path.write_text(
        "\\documentclass{article}\n"
        "\\pagestyle{empty}\n"
        "\\begin{document}\n"
        "$x$\n"
        "\\end{document}\n"
    )
    if dvi_path.exists():
        dvi_path.unlink()
    if svg_path.exists():
        svg_path.unlink()

    latex_result = _run_command(
        [*shlex.split(latex_command), "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=target,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    if latex_result is not None:
        return latex_result
    if not dvi_path.exists():
        return RuntimeSmokeResult(checked=True, available=False, error="latex did not produce smoke.dvi")

    dvisvgm_result = _run_command(
        [*shlex.split(dvisvgm_command), dvi_path.name, "-n", "-o", svg_path.name],
        cwd=target,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    if dvisvgm_result is not None:
        return dvisvgm_result
    if not svg_path.exists():
        return RuntimeSmokeResult(checked=True, available=False, error="dvisvgm did not produce smoke.svg")

    return RuntimeSmokeResult(checked=True, available=True)


def _run_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None,
    timeout_seconds: float,
) -> RuntimeSmokeResult | None:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return RuntimeSmokeResult(checked=True, available=False, error=str(exc))
    except subprocess.TimeoutExpired:
        return RuntimeSmokeResult(checked=True, available=False, error=f"command timed out: {argv[0]}")

    if completed.returncode == 0:
        return None

    message = (completed.stderr or completed.stdout or f"command failed: {argv[0]}").strip()
    return RuntimeSmokeResult(checked=True, available=False, error=message)
