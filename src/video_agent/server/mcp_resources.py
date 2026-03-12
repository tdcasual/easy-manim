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
    target = context.artifact_store.task_dir(task_id) / Path(relative_path)
    if target.suffix == ".json":
        return json.dumps(json.loads(target.read_text()), indent=2)
    return target.read_text()
