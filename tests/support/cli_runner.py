from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_repo_module_json(module: str, *args: str) -> dict[str, Any]:
    env = dict(os.environ)
    repo_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(repo_root / "src")

    completed = subprocess.run(
        [sys.executable, "-m", module, *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)

    return json.loads(completed.stdout)
