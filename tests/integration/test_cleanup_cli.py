import subprocess
import sys
from pathlib import Path

from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.server.app import create_app_context



def test_cleanup_cli_dry_run_reports_old_completed_tasks(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data")
    context = create_app_context(settings)
    task_result = context.task_service.create_video_task(prompt="draw a circle")

    task = context.store.get_task(task_result.task_id)
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    context.store.update_task(task)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.cleanup.main",
            "--data-dir",
            str(settings.data_dir),
            "--older-than-hours",
            "0",
            "--status",
            "completed",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert task_result.task_id in completed.stdout
    assert completed.returncode == 0
