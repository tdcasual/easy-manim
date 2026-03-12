from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport
from video_agent.observability.logging import serialize_log_event


class ArtifactStore:
    def __init__(self, root: Path, eval_root: Path | None = None) -> None:
        self.root = Path(root)
        self.eval_root = Path(eval_root) if eval_root is not None else self.root.parent / "evals"

    def task_dir(self, task_id: str) -> Path:
        return self.root / task_id

    def ensure_task_dirs(self, task_id: str) -> Path:
        task_dir = self.task_dir(task_id)
        (task_dir / "logs").mkdir(parents=True, exist_ok=True)
        (task_dir / "artifacts" / "previews").mkdir(parents=True, exist_ok=True)
        (task_dir / "validations").mkdir(parents=True, exist_ok=True)
        return task_dir

    def task_snapshot_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "task.json"

    def write_task_snapshot(self, task: VideoTask) -> Path:
        task_dir = self.ensure_task_dirs(task.task_id)
        target = task_dir / "task.json"
        target.write_text(task.model_dump_json(indent=2))
        return target

    def task_log_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "logs" / "events.jsonl"

    def append_task_log(self, task_id: str, event: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "logs" / "events.jsonl"
        with target.open("a", encoding="utf-8") as handle:
            handle.write(serialize_log_event(event))
        return target

    def script_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "current_script.py"

    def write_script(self, task_id: str, script_text: str) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "current_script.py"
        target.write_text(script_text)
        return target

    def final_video_path(self, task_id: str) -> Path:
        return self.ensure_task_dirs(task_id) / "artifacts" / "final_video.mp4"

    def previews_dir(self, task_id: str) -> Path:
        return self.ensure_task_dirs(task_id) / "artifacts" / "previews"

    def validation_report_path(self, task_id: str, version: int = 1) -> Path:
        return self.task_dir(task_id) / "validations" / f"validation_report_v{version}.json"

    def write_validation_report(self, task_id: str, report: ValidationReport, version: int = 1) -> Path:
        target = self.ensure_task_dirs(task_id) / "validations" / f"validation_report_v{version}.json"
        target.write_text(report.model_dump_json(indent=2))
        return target

    def eval_run_dir(self, run_id: str) -> Path:
        target = self.eval_root / run_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    def write_eval_summary(self, run_id: str, payload: dict[str, Any]) -> Path:
        target = self.eval_run_dir(run_id) / "summary.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def write_eval_summary_markdown(self, run_id: str, content: str) -> Path:
        target = self.eval_run_dir(run_id) / "summary.md"
        target.write_text(content)
        return target

    def delete_task_dir(self, task_id: str) -> None:
        shutil.rmtree(self.task_dir(task_id), ignore_errors=True)
