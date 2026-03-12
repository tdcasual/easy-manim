from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from video_agent.adapters.storage.artifact_store import ArtifactStore


class TaskExportService:
    def __init__(self, artifact_store: ArtifactStore) -> None:
        self.artifact_store = artifact_store

    def export_bundle(self, task_id: str, output_path: Path) -> Path:
        task_dir = self.artifact_store.task_dir(task_id)
        if not task_dir.exists():
            raise FileNotFoundError(f"Task directory does not exist: {task_dir}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as bundle:
            for path in sorted(task_dir.rglob("*")):
                if path.is_file():
                    bundle.write(path, arcname=path.relative_to(task_dir).as_posix())
        return output_path
