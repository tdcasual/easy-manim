from pathlib import Path

import pytest

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            multi_agent_workflow_enabled=True,
        )
    )


def _seed_agent(app_context, *, agent_id: str, secret: str, scopes_json: dict | None = None):
    app_context.store.upsert_agent_profile(
        AgentProfile(
            agent_id=agent_id,
            name=agent_id,
        )
    )
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
            scopes_json=scopes_json or {},
        )
    )
    return app_context.agent_identity_service.authenticate(secret)


def _seed_memory(
    app_context,
    *,
    memory_id: str,
    agent_id: str,
    summary_text: str,
) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            summary_text=summary_text,
            summary_digest=f"digest-{memory_id}",
        )
    )


def test_workflow_collaboration_service_recommends_owner_memories_from_root_prompt_and_case_memory(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    _seed_memory(
        app_context,
        memory_id="mem-geometry",
        agent_id="agent-a",
        summary_text="Keep geometry demos clean, centered, and easy to follow.",
    )
    _seed_memory(
        app_context,
        memory_id="mem-irrelevant",
        agent_id="agent-a",
        summary_text="Favor watercolor textures and soft pastoral transitions.",
    )

    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        agent_principal=owner,
    )
    task = app_context.store.get_task(created.task_id)
    assert task is not None
    app_context.case_memory_service.record_review_outcome(
        task,
        summary="Opening needs stronger contrast and a visible motion beat.",
        quality_gate_status="needs_revision",
        quality_scorecard=None,
        failure_contract=None,
        recovery_plan=None,
    )

    recommendations = app_context.workflow_collaboration_service.list_workflow_memory_recommendations(
        created.task_id,
        agent_principal=owner,
    )

    assert recommendations.root_task_id == created.task_id
    assert "draw a circle explainer" in recommendations.query
    assert "stronger contrast" in recommendations.query
    assert recommendations.pinned_memory_ids == []
    assert [item.memory_id for item in recommendations.items[:2]] == [
        "mem-contrast",
        "mem-geometry",
    ]
    assert recommendations.items[0].pinned is False


def test_workflow_collaboration_service_pins_and_unpins_root_memory_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_memory(
        app_context,
        memory_id="mem-style",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise annotations.",
    )

    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        agent_principal=owner,
    )

    pinned = app_context.workflow_collaboration_service.pin_workflow_memory(
        created.task_id,
        memory_id="mem-style",
        agent_principal=owner,
    )
    root_after_pin = app_context.store.get_task(created.task_id)

    assert pinned.root_task_id == created.task_id
    assert pinned.memory_id == "mem-style"
    assert pinned.pinned_memory_ids == ["mem-style"]
    assert "high-contrast diagrams" in (pinned.persistent_memory_context_summary or "")
    assert root_after_pin is not None
    assert root_after_pin.selected_memory_ids == ["mem-style"]
    assert root_after_pin.persistent_memory_context_digest == pinned.persistent_memory_context_digest

    unpinned = app_context.workflow_collaboration_service.unpin_workflow_memory(
        created.task_id,
        memory_id="mem-style",
        agent_principal=owner,
    )
    root_after_unpin = app_context.store.get_task(created.task_id)
    events = app_context.task_service.get_task_events(created.task_id)
    workflow_memory_events = [event for event in events if event["event_type"].startswith("workflow_memory_")]

    assert unpinned.root_task_id == created.task_id
    assert unpinned.memory_id == "mem-style"
    assert unpinned.pinned_memory_ids == []
    assert unpinned.persistent_memory_context_summary is None
    assert root_after_unpin is not None
    assert root_after_unpin.selected_memory_ids == []
    assert root_after_unpin.persistent_memory_context_summary is None
    assert [event["event_type"] for event in workflow_memory_events] == [
        "workflow_memory_pinned",
        "workflow_memory_unpinned",
    ]


def test_workflow_collaboration_service_denies_non_owner_workflow_memory_management(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    intruder = _seed_agent(
        app_context,
        agent_id="agent-b",
        secret="agent-b-secret",
        scopes_json={"allow": ["task:read", "task:mutate"]},
    )
    _seed_memory(
        app_context,
        memory_id="mem-style",
        agent_id="agent-a",
        summary_text="Prefer high-contrast diagrams with concise annotations.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        agent_principal=owner,
    )

    with pytest.raises(PermissionError):
        app_context.workflow_collaboration_service.list_workflow_memory_recommendations(
            created.task_id,
            agent_principal=intruder,
        )

    with pytest.raises(PermissionError):
        app_context.workflow_collaboration_service.pin_workflow_memory(
            created.task_id,
            memory_id="mem-style",
            agent_principal=intruder,
        )


def test_workflow_collaboration_service_grants_capability_scoped_access(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_agent(app_context, agent_id="agent-b", secret="agent-b-secret", scopes_json={"allow": ["task:read"]})
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        agent_principal=owner,
    )

    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        capabilities=["review_bundle:read"],
        agent_principal=owner,
    )

    allowed_task = app_context.workflow_collaboration_service.require_workflow_access(
        created.task_id,
        "agent-b",
        capability="review_bundle:read",
    )

    assert allowed_task.task_id == created.task_id

    try:
        app_context.workflow_collaboration_service.require_workflow_access(
            created.task_id,
            "agent-b",
            capability="review_decision:write",
        )
    except PermissionError as exc:
        assert str(exc) == "agent_access_denied"
    else:
        raise AssertionError("Expected review_decision:write to remain denied")


def test_workflow_collaboration_service_records_participant_audit_events(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_agent(app_context, agent_id="agent-b", secret="agent-b-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        agent_principal=owner,
    )

    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        capabilities=["review_bundle:read"],
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.remove_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        agent_principal=owner,
    )

    events = app_context.task_service.get_task_events(created.task_id)
    participant_events = [event for event in events if event["event_type"].startswith("workflow_participant_")]

    assert [event["event_type"] for event in participant_events] == [
        "workflow_participant_upserted",
        "workflow_participant_removed",
    ]


def test_workflow_collaboration_service_no_longer_exposes_legacy_discussion_helpers(
    tmp_path: Path,
) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    assert not hasattr(app_context.workflow_collaboration_service, "add_discussion_message")
    assert not hasattr(app_context.workflow_collaboration_service, "add_agent_discussion_reply")
    assert not hasattr(app_context.workflow_collaboration_service, "list_discussion_events")


def test_workflow_collaboration_service_routes_collaborator_revision_to_owner_task_lineage(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_agent(app_context, agent_id="agent-b", secret="agent-b-secret", scopes_json={"allow": ["task:read"]})
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        capabilities=["review_bundle:read", "review_decision:write"],
        agent_principal=owner,
    )

    revised = app_context.workflow_collaboration_service.revise_video_task(
        created.task_id,
        feedback="make it blue",
        actor_agent_id="agent-b",
        session_id="session-1",
    )
    task = app_context.store.get_task(revised.task_id)

    assert task is not None
    assert task.agent_id == "agent-a"
    assert task.parent_task_id == created.task_id


def test_workflow_collaboration_service_builds_workflow_summary_from_active_participants_and_events(
    tmp_path: Path,
) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_agent(app_context, agent_id="agent-b", secret="agent-b-secret")
    _seed_agent(app_context, agent_id="agent-c", secret="agent-c-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        agent_principal=owner,
    )

    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        capabilities=["review_bundle:read", "review_decision:write"],
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-c",
        role="repairer",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.remove_workflow_participant(
        created.task_id,
        participant_agent_id="agent-c",
        agent_principal=owner,
    )

    summary = app_context.workflow_collaboration_service.build_workflow_summary(created.task_id)

    assert summary.root_task_id == created.task_id
    assert summary.participant_count == 1
    assert summary.participants_by_role == {"reviewer": 1}
    assert summary.capability_counts == {
        "review_bundle:read": 1,
        "review_decision:write": 1,
    }
    assert [participant.agent_id for participant in summary.participants] == ["agent-b"]
    assert [event.event_type for event in summary.recent_events] == [
        "workflow_participant_upserted",
        "workflow_participant_upserted",
        "workflow_participant_removed",
    ]
    assert summary.recent_events[-1].agent_id == "agent-c"
    assert summary.recent_events[-1].removed is True


def test_workflow_collaboration_service_builds_runtime_summary_across_root_workflows(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_agent(app_context, agent_id="agent-b", secret="agent-b-secret")
    _seed_agent(app_context, agent_id="agent-c", secret="agent-c-secret")
    _seed_agent(app_context, agent_id="agent-d", secret="agent-d-secret")

    first = app_context.task_service.create_video_task(
        prompt="draw a circle",
        agent_principal=owner,
    )
    second = app_context.task_service.create_video_task(
        prompt="draw a square",
        agent_principal=owner,
    )

    app_context.workflow_collaboration_service.upsert_workflow_participant(
        first.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        second.task_id,
        participant_agent_id="agent-c",
        role="repairer",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        second.task_id,
        participant_agent_id="agent-d",
        role="verifier",
        agent_principal=owner,
    )

    summary = app_context.workflow_collaboration_service.build_runtime_summary()

    assert summary.workflow_count == 2
    assert summary.participant_count == 3
    assert summary.participants_by_role == {
        "repairer": 1,
        "reviewer": 1,
        "verifier": 1,
    }
    assert summary.capability_counts == {
        "review_bundle:read": 3,
        "review_decision:write": 2,
    }
    assert [event.event_type for event in summary.recent_events] == [
        "workflow_participant_upserted",
        "workflow_participant_upserted",
        "workflow_participant_upserted",
    ]
    assert {event.root_task_id for event in summary.recent_events} == {
        first.task_id,
        second.task_id,
    }


def test_workflow_collaboration_service_builds_role_aware_memory_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    owner = _seed_agent(app_context, agent_id="agent-a", secret="agent-a-secret")
    _seed_memory(
        app_context,
        memory_id="mem-style",
        agent_id="agent-a",
        summary_text="Prefer light backgrounds, concise labels, and visible motion in the opening beat.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        memory_ids=["mem-style"],
        agent_principal=owner,
    )
    task = app_context.store.get_task(created.task_id)
    assert task is not None

    app_context.case_memory_service.record_planner_state(task)
    app_context.case_memory_service.record_review_outcome(
        task,
        summary="Preview opens too quietly and needs stronger contrast.",
        quality_gate_status="needs_revision",
        quality_scorecard=None,
        failure_contract={
            "recommended_action": "repair",
            "repair_strategy": "Increase contrast and add a visible opening motion beat.",
        },
        recovery_plan={
            "selected_action": "repair",
        },
    )

    memory_context = app_context.workflow_collaboration_service.build_workflow_memory_context(created.task_id)

    assert memory_context.root_task_id == created.task_id
    assert memory_context.agent_id == "agent-a"
    assert memory_context.shared_memory_ids == ["mem-style"]
    assert memory_context.planner.role == "planner"
    assert memory_context.reviewer.role == "reviewer"
    assert memory_context.repairer.role == "repairer"
    assert "light backgrounds" in memory_context.planner.summary
    assert "Preserve core prompt intent: draw a circle." in memory_context.planner.summary
    assert "needs_revision" in memory_context.reviewer.summary
    assert "Preview opens too quietly" in memory_context.reviewer.summary
    assert "Increase contrast and add a visible opening motion beat." in memory_context.repairer.summary
    assert memory_context.repairer.item_count >= 2
