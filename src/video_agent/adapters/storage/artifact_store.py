from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from video_agent.domain.models import VideoTask
from video_agent.domain.case_memory_models import CaseMemorySnapshot
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

    def scene_plan_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "scene_plan.json"

    def write_scene_plan(self, task_id: str, payload: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "scene_plan.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def scene_spec_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "scene_spec.json"

    def write_scene_spec(self, task_id: str, payload: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "scene_spec.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def read_scene_spec(self, task_id: str) -> dict[str, Any] | None:
        target = self.scene_spec_path(task_id)
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def recovery_plan_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "recovery_plan.json"

    def write_recovery_plan(self, task_id: str, payload: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "recovery_plan.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def read_recovery_plan(self, task_id: str) -> dict[str, Any] | None:
        target = self.recovery_plan_path(task_id)
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def quality_score_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "quality_score.json"

    def write_quality_score(self, task_id: str, payload: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "quality_score.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def read_quality_score(self, task_id: str) -> dict[str, Any] | None:
        target = self.quality_score_path(task_id)
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def failure_context_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "failure_context.json"

    def write_failure_context(self, task_id: str, payload: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "failure_context.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def failure_contract_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "artifacts" / "failure_contract.json"

    def write_failure_contract(self, task_id: str, payload: dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(task_id) / "artifacts" / "failure_contract.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def read_failure_contract(self, task_id: str) -> dict[str, Any] | None:
        target = self.failure_contract_path(task_id)
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def case_memory_path(self, root_task_id: str) -> Path:
        return self.task_dir(root_task_id) / "artifacts" / "case_memory.json"

    def write_case_memory(self, root_task_id: str, payload: CaseMemorySnapshot | dict[str, Any]) -> Path:
        target = self.ensure_task_dirs(root_task_id) / "artifacts" / "case_memory.json"
        if isinstance(payload, CaseMemorySnapshot):
            target.write_text(payload.model_dump_json(indent=2))
        else:
            target.write_text(json.dumps(payload, indent=2))
        return target

    def read_case_memory(self, root_task_id: str) -> dict[str, Any] | None:
        target = self.case_memory_path(root_task_id)
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def final_video_path(self, task_id: str) -> Path:
        return self.ensure_task_dirs(task_id) / "artifacts" / "final_video.mp4"

    def promote_final_video(self, task_id: str, rendered_video_path: Path) -> Path:
        source = Path(rendered_video_path)
        target = self.final_video_path(task_id)
        if source == target:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        shutil.move(str(source), str(target))
        return target

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

    def eval_run_manifest_path(self, run_id: str) -> Path:
        return self.eval_root / run_id / "run_manifest.json"

    def write_eval_run_manifest(self, run_id: str, payload: dict[str, Any]) -> Path:
        target = self.eval_run_dir(run_id) / "run_manifest.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def read_eval_run_manifest(self, run_id: str) -> dict[str, Any] | None:
        target = self.eval_run_manifest_path(run_id)
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def write_eval_summary(self, run_id: str, payload: dict[str, Any]) -> Path:
        target = self.eval_run_dir(run_id) / "summary.json"
        target.write_text(json.dumps(payload, indent=2))
        return target

    def read_eval_summary(self, run_id: str) -> dict[str, Any] | None:
        target = self.eval_root / run_id / "summary.json"
        if not target.exists():
            return None
        return json.loads(target.read_text())

    def list_eval_summaries(self) -> list[dict[str, Any]]:
        if not self.eval_root.exists():
            return []
        items: list[dict[str, Any]] = []
        for summary_path in sorted(self.eval_root.glob("*/summary.json"), reverse=True):
            items.append(json.loads(summary_path.read_text()))
        return items

    def write_eval_summary_markdown(self, run_id: str, content: str) -> Path:
        target = self.eval_run_dir(run_id) / "summary.md"
        target.write_text(content)
        return target

    def write_eval_reviewer_digest(self, run_id: str, content: str) -> Path:
        target = self.eval_run_dir(run_id) / "review_digest.md"
        target.write_text(content)
        return target

    def task_relative_path(self, task_id: str, path: Path) -> Path:
        return Path(path).relative_to(self.task_dir(task_id))

    def resource_uri(self, task_id: str, path: Path) -> str:
        return f"video-task://{task_id}/{self.task_relative_path(task_id, path).as_posix()}"

    def delete_task_dir(self, task_id: str) -> None:
        shutil.rmtree(self.task_dir(task_id), ignore_errors=True)
