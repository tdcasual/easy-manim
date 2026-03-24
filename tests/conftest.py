import os
from pathlib import Path
import sys

import pytest

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings


@pytest.fixture(autouse=True)
def ensure_venv_console_scripts_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Our tests spawn `easy-manim-*` console scripts. When running tests without
    activating the venv, those scripts exist in `Path(sys.executable).parent`
    but that directory might not be on PATH.
    """
    # Avoid `.resolve()` here: in some environments `sys.executable` is a
    # symlink inside the venv, and resolving it points at the base Python
    # install instead of the venv `bin/` directory that contains the
    # `easy-manim-*` entrypoints.
    bin_dir = str(Path(sys.executable).parent)
    existing = os.environ.get("PATH", "")
    parts = existing.split(os.pathsep) if existing else []
    if bin_dir not in parts:
        monkeypatch.setenv("PATH", os.pathsep.join([bin_dir, existing]) if existing else bin_dir)


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    return settings
