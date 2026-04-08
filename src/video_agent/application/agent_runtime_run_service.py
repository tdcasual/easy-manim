from __future__ import annotations

from collections.abc import Callable

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.domain.agent_runtime_run_models import AgentRuntimeRun


class AgentRuntimeRunService:
    def __init__(
        self,
        *,
        create_run: Callable[[AgentRuntimeRun], AgentRuntimeRun],
        list_runs: Callable[[str | None, str | None, int], list[AgentRuntimeRun]],
    ) -> None:
        self.create_run = create_run
        self.list_runs = list_runs

    def record_authentication(
        self,
        *,
        session_id: str,
        principal: AgentPrincipal,
        source_kind: str,
    ) -> AgentRuntimeRun:
        return self.create_run(
            AgentRuntimeRun(
                session_id=session_id,
                agent_id=principal.agent_id,
                source_kind=source_kind,
                trigger_kind="authenticate",
                summary=f"Authenticated runtime {principal.runtime_definition.name}",
            )
        )

    def record_task_invocation(
        self,
        *,
        session_id: str | None,
        principal: AgentPrincipal | None,
        source_kind: str,
        trigger_kind: str,
        task_id: str,
        thread_id: str | None = None,
        iteration_id: str | None = None,
        summary: str | None = None,
    ) -> AgentRuntimeRun | None:
        if session_id is None or principal is None:
            return None
        return self.create_run(
            AgentRuntimeRun(
                session_id=session_id,
                agent_id=principal.agent_id,
                source_kind=source_kind,
                trigger_kind=trigger_kind,
                task_id=task_id,
                thread_id=thread_id,
                iteration_id=iteration_id,
                summary=summary,
            )
        )
