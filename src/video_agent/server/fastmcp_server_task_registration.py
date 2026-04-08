from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.app import AppContext
from video_agent.server.mcp_tools import (
    accept_best_version_tool,
    apply_review_decision_tool,
    cancel_video_task_tool,
    create_video_task_tool,
    get_failure_contract_tool,
    get_metrics_snapshot_tool,
    get_quality_score_tool,
    get_recovery_plan_tool,
    get_review_bundle_tool,
    get_runtime_status_tool,
    get_scene_spec_tool,
    get_task_events_tool,
    get_video_result_tool,
    get_video_task_tool,
    list_video_tasks_tool,
    list_workflow_participants_tool,
    remove_workflow_participant_tool,
    retry_video_task_tool,
    revise_video_task_tool,
    upsert_workflow_participant_tool,
)


def register_task_tools(
    *,
    mcp: FastMCP,
    context: AppContext,
    current_principal: Callable[[Context | None], AgentPrincipal | None],
    current_session_id: Callable[[Context | None], str | None],
) -> None:
    @mcp.tool(name="create_video_task")
    def create_video_task(
        prompt: str,
        idempotency_key: str | None = None,
        output_profile: dict[str, Any] | None = None,
        style_hints: dict[str, Any] | None = None,
        validation_profile: dict[str, Any] | None = None,
        strategy_prompt_cluster: str | None = None,
        feedback: str | None = None,
        memory_ids: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return create_video_task_tool(
            context,
            {
                "prompt": prompt,
                "idempotency_key": idempotency_key,
                "output_profile": output_profile,
                "style_hints": style_hints,
                "validation_profile": validation_profile,
                "strategy_prompt_cluster": strategy_prompt_cluster,
                "feedback": feedback,
                "memory_ids": memory_ids,
                "session_id": current_session_id(ctx),
                "source_kind": "mcp_transport",
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_video_task")
    def get_video_task(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_video_task_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_failure_contract")
    def get_failure_contract(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_failure_contract_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_scene_spec")
    def get_scene_spec(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_scene_spec_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_recovery_plan")
    def get_recovery_plan(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_recovery_plan_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_quality_score")
    def get_quality_score(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_quality_score_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="list_video_tasks")
    def list_video_tasks(limit: int = 50, status: str | None = None, ctx: Context | None = None) -> dict[str, Any]:
        return list_video_tasks_tool(
            context,
            {"limit": limit, "status": status},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_task_events")
    def get_task_events(task_id: str, limit: int = 200, ctx: Context | None = None) -> dict[str, Any]:
        return get_task_events_tool(
            context,
            {"task_id": task_id, "limit": limit},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_review_bundle")
    def get_review_bundle(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_review_bundle_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="list_workflow_participants")
    def list_workflow_participants(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return list_workflow_participants_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="upsert_workflow_participant")
    def upsert_workflow_participant(
        task_id: str,
        agent_id: str,
        role: str,
        capabilities: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return upsert_workflow_participant_tool(
            context,
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "role": role,
                "capabilities": capabilities,
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="remove_workflow_participant")
    def remove_workflow_participant(task_id: str, agent_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return remove_workflow_participant_tool(
            context,
            {
                "task_id": task_id,
                "agent_id": agent_id,
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="apply_review_decision")
    def apply_review_decision(
        task_id: str,
        review_decision: dict[str, Any],
        memory_ids: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return apply_review_decision_tool(
            context,
            {
                "task_id": task_id,
                "review_decision": review_decision,
                "memory_ids": memory_ids,
                "session_id": current_session_id(ctx),
                "source_kind": "mcp_transport",
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_metrics_snapshot")
    def get_metrics_snapshot() -> dict[str, Any]:
        return get_metrics_snapshot_tool(context, {})

    @mcp.tool(name="get_runtime_status")
    def get_runtime_status() -> dict[str, Any]:
        return get_runtime_status_tool(context, {})

    @mcp.tool(name="revise_video_task")
    def revise_video_task(
        base_task_id: str,
        feedback: str,
        preserve_working_parts: bool = True,
        memory_ids: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return revise_video_task_tool(
            context,
            {
                "base_task_id": base_task_id,
                "feedback": feedback,
                "preserve_working_parts": preserve_working_parts,
                "memory_ids": memory_ids,
                "session_id": current_session_id(ctx),
                "source_kind": "mcp_transport",
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="retry_video_task")
    def retry_video_task(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return retry_video_task_tool(
            context,
            {
                "task_id": task_id,
                "session_id": current_session_id(ctx),
                "source_kind": "mcp_transport",
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_video_result")
    def get_video_result(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_video_result_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="cancel_video_task")
    def cancel_video_task(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return cancel_video_task_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="accept_best_version")
    def accept_best_version(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return accept_best_version_tool(
            context,
            {"task_id": task_id},
            agent_principal=current_principal(ctx),
        )
