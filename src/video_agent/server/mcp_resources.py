from __future__ import annotations

import json
from pathlib import Path

from video_agent.server.app import AppContext



def read_resource(context: AppContext, resource_uri: str) -> str:
    prefix = "video-task://"
    if not resource_uri.startswith(prefix):
        raise ValueError(f"Unsupported resource URI: {resource_uri}")

    path = resource_uri[len(prefix) :]
    task_id, relative_path = path.split("/", 1)
    task_root = context.artifact_store.task_dir(task_id).resolve()
    target = (task_root / Path(relative_path)).resolve()
    if target != task_root and task_root not in target.parents:
        raise ValueError(f"Resource path escapes task root: {resource_uri}")
    if target.suffix == ".json":
        return json.dumps(json.loads(target.read_text()), indent=2)
    return target.read_text()
