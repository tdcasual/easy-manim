import subprocess
import sys
import zipfile
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context



def test_export_cli_writes_bundle_zip(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data")
    context = create_app_context(settings)
    created = context.task_service.create_video_task(prompt="draw a square")
    context.artifact_store.append_task_log(created.task_id, {"message": "test log"})
    bundle_path = tmp_path / "bundle.zip"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.export.main",
            "--data-dir",
            str(settings.data_dir),
            "--task-id",
            created.task_id,
            "--output",
            str(bundle_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    with zipfile.ZipFile(bundle_path) as bundle:
        assert "task.json" in bundle.namelist()
        assert "logs/events.jsonl" in bundle.namelist()
