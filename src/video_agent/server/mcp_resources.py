from __future__ import annotations

import json
from pathlib import Path

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.app import AppContext



def read_resource(context: AppContext, resource_uri: str) -> str:
    return _read_resource(context, resource_uri, agent_id=None)


def read_resource_for_agent(context: AppContext, resource_uri: str, agent_id: str) -> str:
    return _read_resource(context, resource_uri, agent_id=agent_id)


def authorize_resource_access(
    context: AppContext,
    task_id: str,
    *,
    agent_principal: AgentPrincipal | None = None,
) -> None:
    if context.settings.auth_mode != "required":
        return
    if agent_principal is None:
        raise PermissionError("agent_not_authenticated")
    context.task_service.require_task_access(task_id, agent_principal.agent_id)


def _read_resource(context: AppContext, resource_uri: str, agent_id: str | None) -> str:
    prefix = "video-task://"
    if not resource_uri.startswith(prefix):
        raise ValueError(f"Unsupported resource URI: {resource_uri}")

    path = resource_uri[len(prefix) :]
    task_id, relative_path = path.split("/", 1)
    if agent_id is not None:
        context.task_service.require_task_access(task_id, agent_id)
    task_root = context.artifact_store.task_dir(task_id).resolve()
    target = (task_root / Path(relative_path)).resolve()
    if target != task_root and task_root not in target.parents:
        raise ValueError(f"Resource path escapes task root: {resource_uri}")
    if target.suffix == ".json":
        return json.dumps(json.loads(target.read_text()), indent=2)
    return target.read_text()
