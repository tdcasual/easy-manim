from __future__ import annotations

import argparse
from pathlib import Path

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.application.export_service import TaskExportService
from video_agent.server.main import build_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export one easy-manim task bundle")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir)
    service = TaskExportService(ArtifactStore(settings.artifact_root))
    output_path = service.export_bundle(args.task_id, args.output)
    print(output_path)


if __name__ == "__main__":
    main()
