from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from video_agent.adapters.storage.artifact_store import ArtifactStore


class QABundleService:
    def __init__(self, artifact_store: ArtifactStore) -> None:
        self.artifact_store = artifact_store

    def export_run_bundle(self, run_id: str, output_path: Path) -> Path:
        run_dir = self.artifact_store.eval_root / run_id
        if not run_dir.exists():
            raise FileNotFoundError(f"Evaluation run does not exist: {run_dir}")

        summary_json_path = run_dir / "summary.json"
        summary_markdown_path = run_dir / "summary.md"
        if not summary_json_path.exists():
            raise FileNotFoundError(f"Evaluation summary does not exist: {summary_json_path}")
        if not summary_markdown_path.exists():
            raise FileNotFoundError(f"Evaluation report does not exist: {summary_markdown_path}")

        payload = json.loads(summary_json_path.read_text())
        task_ids: list[str] = []
        for item in payload.get("items", []):
            task_id = item.get("task_id")
            if isinstance(task_id, str) and task_id not in task_ids:
                task_ids.append(task_id)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(summary_json_path, arcname="summary.json")
            bundle.write(summary_markdown_path, arcname="summary.md")
            for task_id in task_ids:
                task_dir = self.artifact_store.task_dir(task_id)
                if not task_dir.exists():
                    raise FileNotFoundError(f"Task directory does not exist: {task_dir}")
                for path in sorted(task_dir.rglob("*")):
                    if path.is_file():
                        bundle.write(path, arcname=f"tasks/{task_id}/{path.relative_to(task_dir).as_posix()}")
        return output_path
