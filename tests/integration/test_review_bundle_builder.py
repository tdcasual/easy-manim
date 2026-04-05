import json
from pathlib import Path
import sys
import types
from collections.abc import Callable

import pytest

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.application.review_bundle_builder import ReviewBundleBuilder
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.quality_models import QualityScorecard
from tests.support import bootstrapped_settings


def _with_temporary_mcp_shim(fn: Callable[[], object]) -> object:
    if "mcp.server.fastmcp" in sys.modules:
        return fn()

    injected: dict[str, types.ModuleType] = {}
    original: dict[str, types.ModuleType] = {}
    module_names = ("mcp", "mcp.server", "mcp.server.fastmcp")
    for name in module_names:
        module = sys.modules.get(name)
        if module is not None:
            original[name] = module

    mcp_module = types.ModuleType("mcp")
    mcp_server_module = types.ModuleType("mcp.server")
    mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class _Context:  # pragma: no cover - test import shim
        pass

    mcp_fastmcp_module.Context = _Context
    mcp_server_module.fastmcp = mcp_fastmcp_module
    mcp_module.server = mcp_server_module

    injected["mcp"] = mcp_module
    injected["mcp.server"] = mcp_server_module
    injected["mcp.server.fastmcp"] = mcp_fastmcp_module

    try:
        sys.modules.update(injected)
        return fn()
    finally:
        for name in module_names:
            previous = original.get(name)
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def _create_app_context(settings: Settings):
    from video_agent.server.app import create_app_context

    return create_app_context(settings)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_pipeline_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "mkdir -p \"$2\"\n"
        "printf 'normal-video' > \"$2/final_video.mp4\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$2\"\n"
        "printf 'frame1' > \"$2/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
        )
    )


def _build_required_auth_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
        )
    )


def _seed_required_agent(app_context, agent_id: str, secret: str) -> None:
    app_context.store.upsert_agent_profile(AgentProfile(agent_id=agent_id, name=agent_id))
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def _seed_agent_memory(app_context, *, memory_id: str, agent_id: str, summary_text: str) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            summary_text=summary_text,
            summary_digest=f"digest-{memory_id}",
        )
    )


def test_review_bundle_builder_collects_task_result_and_memory(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert bundle.task_id == created.task_id
    assert bundle.root_task_id == created.task_id
    assert bundle.attempt_count == 0
    assert bundle.child_attempt_count == 0
    assert bundle.prompt == "draw a circle"
    assert bundle.feedback is None
    assert bundle.display_title is not None
    assert bundle.status == "queued"
    assert bundle.phase == "queued"
    assert bundle.latest_validation_summary == {}
    assert bundle.failure_contract is None
    assert bundle.task_events
    assert bundle.task_events[0]["event_type"] == "task_created"
    assert bundle.session_memory_summary
    assert "Goal: draw a circle" in bundle.session_memory_summary
    assert bundle.video_resource is None
    assert bundle.preview_frame_resources == []
    assert bundle.script_resource is None
    assert bundle.validation_report_resource is None


def test_review_bundle_builder_omits_legacy_video_discussion_surface(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle with a bold title card",
        session_id="session-1",
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert "video_discussion_surface" not in bundle.model_dump(mode="json")


def test_review_bundle_builder_respects_agent_scoping(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    agent_a = app_context.agent_identity_service.authenticate("agent-a-secret")
    agent_b = app_context.agent_identity_service.authenticate("agent-b-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        agent_principal=agent_a,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )

    bundle = builder.build(task_id=created.task_id, agent_principal=agent_a)
    assert bundle.task_id == created.task_id

    with pytest.raises(PermissionError):
        builder.build(task_id=created.task_id, agent_principal=agent_b)


def test_review_bundle_builder_derives_acceptance_blockers_and_trace(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_fake_pipeline_settings(tmp_path)))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    task = app_context.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.FAILED
    task.phase = TaskPhase.FAILED
    task.quality_gate_status = "needs_revision"
    app_context.store.update_task(task)
    app_context.store.upsert_task_quality_score(
        created.task_id,
        QualityScorecard(
            task_id=created.task_id,
            accepted=False,
            must_fix_issues=["timing_overlap"],
        ),
    )
    app_context.artifact_store.write_recovery_plan(
        created.task_id,
        {
            "selected_action": "repair",
            "repair_recipe": "tighten timing and layout",
        },
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert bundle.must_fix_issue_codes == ["timing_overlap"]
    assert "quality_gate_not_accepted" in bundle.acceptance_blockers
    assert "must_fix_issue_codes" in bundle.acceptance_blockers
    assert bundle.decision_trace["quality_gate_status"] == "needs_revision"
    assert bundle.decision_trace["recovery_selected_action"] == "repair"


def test_review_bundle_builder_exposes_shared_case_memory(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.quality_gate_min_score = 0.95
    settings.multi_agent_workflow_enabled = True
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(settings))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    app_context.worker.run_once()

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=None)

    assert bundle.case_memory["planner_notes"]
    assert bundle.case_memory["review_findings"]
    assert bundle.case_memory["repair_constraints"]
    assert bundle.case_memory["delivery_invariants"]


def test_review_bundle_builder_exposes_collaboration_summary(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    _seed_required_agent(app_context, "agent-c", "agent-c-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-c",
        role="repairer",
        agent_principal=owner,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.collaboration_summary.root_task_id == created.task_id
    assert bundle.collaboration_summary.participant_count == 2
    assert bundle.collaboration_summary.participants_by_role == {
        "repairer": 1,
        "reviewer": 1,
    }
    assert bundle.collaboration_summary.capability_counts == {
        "review_bundle:read": 2,
        "review_decision:write": 1,
    }
    assert [participant.agent_id for participant in bundle.collaboration_summary.participants] == [
        "agent-b",
        "agent-c",
    ]
    assert [event.event_type for event in bundle.collaboration_summary.recent_events] == [
        "workflow_participant_upserted",
        "workflow_participant_upserted",
    ]


def test_review_bundle_builder_exposes_collaboration_memory_context(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-style",
        agent_id="agent-a",
        summary_text="Prefer light backgrounds, concise labels, and visible motion in the opening beat.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
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

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.collaboration_memory_context is not None
    assert bundle.collaboration_memory_context.root_task_id == created.task_id
    assert bundle.collaboration_memory_context.shared_memory_ids == ["mem-style"]
    assert "light backgrounds" in bundle.collaboration_memory_context.planner.summary
    assert "needs_revision" in bundle.collaboration_memory_context.reviewer.summary
    assert "visible opening motion beat" in bundle.collaboration_memory_context.repairer.summary


def test_review_bundle_builder_exposes_owner_workflow_memory_recommendations(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
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

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.workflow_memory_recommendations is not None
    assert bundle.workflow_memory_recommendations.root_task_id == created.task_id
    assert "stronger contrast" in bundle.workflow_memory_recommendations.query
    assert bundle.workflow_memory_recommendations.items[0].memory_id == "mem-contrast"
    assert bundle.workflow_memory_recommendations.items[0].pinned is False


def test_review_bundle_builder_hides_workflow_memory_recommendations_from_collaborator(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    collaborator = app_context.agent_identity_service.authenticate("agent-b-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        agent_principal=owner,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=collaborator)

    assert bundle.workflow_memory_recommendations is None


def test_review_bundle_builder_exposes_owner_workflow_memory_action_contract(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-pinned",
        agent_id="agent-a",
        summary_text="Geometry layout guidance for centered diagrams.",
    )
    _seed_agent_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
        memory_ids=["mem-pinned"],
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

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.workflow_memory_action_contract is not None
    assert bundle.workflow_memory_action_contract.review_decision_field == "review_decision"
    assert bundle.workflow_memory_action_contract.pin_field == "pin_workflow_memory_ids"
    assert bundle.workflow_memory_action_contract.unpin_field == "unpin_workflow_memory_ids"
    assert bundle.workflow_memory_action_contract.response_state_field == "workflow_memory_state"
    assert bundle.workflow_memory_action_contract.supports_batch_updates is True
    examples = {example.name: example for example in bundle.workflow_memory_action_contract.examples}
    assert examples["pin"].payload["pin_workflow_memory_ids"] == ["mem-contrast"]
    assert examples["pin"].payload["review_decision"]["decision"] == "revise"
    assert examples["unpin"].payload["unpin_workflow_memory_ids"] == ["mem-pinned"]
    assert examples["replace"].payload["pin_workflow_memory_ids"] == ["mem-contrast"]
    assert examples["replace"].payload["unpin_workflow_memory_ids"] == ["mem-pinned"]


def test_review_bundle_builder_hides_workflow_memory_action_contract_from_collaborator(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    collaborator = app_context.agent_identity_service.authenticate("agent-b-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        agent_principal=owner,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=collaborator)

    assert bundle.workflow_memory_action_contract is None


def test_review_bundle_builder_exposes_owner_workflow_review_controls(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-pinned",
        agent_id="agent-a",
        summary_text="Geometry layout guidance for centered diagrams.",
    )
    _seed_agent_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
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
    app_context.workflow_collaboration_service.pin_workflow_memory(
        created.task_id,
        memory_id="mem-pinned",
        agent_principal=owner,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.workflow_review_controls is not None
    assert bundle.workflow_review_controls.can_manage_workflow_memory is True
    assert bundle.workflow_review_controls.workflow_memory_state.pinned_memory_ids == ["mem-pinned"]
    assert bundle.workflow_review_controls.workflow_memory_state.root_task_id == created.task_id
    assert [event.event_type for event in bundle.workflow_review_controls.recent_memory_events] == [
        "workflow_memory_pinned"
    ]
    assert bundle.workflow_review_controls.workflow_memory_recommendations.root_task_id == created.task_id
    assert bundle.workflow_review_controls.workflow_memory_action_contract is not None
    assert bundle.workflow_review_controls.workflow_memory_action_contract.pin_field == "pin_workflow_memory_ids"
    assert bundle.workflow_review_controls.status_summary is not None
    assert bundle.workflow_review_controls.status_summary.recommended_action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.status_summary.latest_workflow_memory_event_type == "workflow_memory_pinned"
    assert bundle.workflow_review_controls.status_summary.latest_workflow_memory_event_at is not None
    assert bundle.workflow_review_controls.action_sections is not None
    assert [section.section_id for section in bundle.workflow_review_controls.action_sections.items] == [
        "recommended",
        "available",
        "blocked",
    ]
    assert bundle.workflow_review_controls.panel_header is not None
    assert bundle.workflow_review_controls.panel_header.tone == "attention"
    assert bundle.workflow_review_controls.panel_header.highlighted_event is not None
    assert bundle.workflow_review_controls.panel_header.highlighted_event.event_type == "workflow_memory_pinned"
    badge_values = {badge.badge_id: badge.value for badge in bundle.workflow_review_controls.panel_header.badges}
    assert badge_values["recommended_action"] == "pin_and_revise"
    assert badge_values["pending_memory"] == "1"
    assert badge_values["acceptance_blockers"] == "1"
    assert bundle.workflow_review_controls.applied_action_feedback is not None
    assert bundle.workflow_review_controls.applied_action_feedback.event_type == "workflow_memory_pinned"
    assert bundle.workflow_review_controls.applied_action_feedback.memory_id == "mem-pinned"
    assert bundle.workflow_review_controls.applied_action_feedback.follow_up_action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.render_contract is not None
    assert bundle.workflow_review_controls.render_contract.panel_tone == "attention"
    assert bundle.workflow_review_controls.render_contract.display_priority == "high"
    assert bundle.workflow_review_controls.render_contract.section_order == ["recommended", "available", "blocked"]
    assert bundle.workflow_review_controls.render_contract.default_focus_section_id == "recommended"
    assert bundle.workflow_review_controls.render_contract.default_expanded_section_ids == ["recommended", "blocked"]
    assert bundle.workflow_review_controls.render_contract.badge_order == [
        "recommended_action",
        "pending_memory",
        "acceptance_blockers",
    ]
    assert bundle.workflow_review_controls.render_contract.sticky_primary_action_emphasis == "strong"
    section_presentations = {
        item.section_id: item for item in bundle.workflow_review_controls.render_contract.section_presentations
    }
    assert section_presentations["recommended"].tone == "accent"
    assert section_presentations["recommended"].collapsible is False
    assert section_presentations["blocked"].tone == "muted"
    assert section_presentations["blocked"].collapsible is True
    assert bundle.workflow_review_controls.render_contract.sticky_primary_action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.render_contract.applied_feedback_dismissible is True


def test_review_bundle_builder_hides_workflow_review_controls_from_collaborator(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    _seed_required_agent(app_context, "agent-b", "agent-b-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    collaborator = app_context.agent_identity_service.authenticate("agent-b-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
        agent_principal=owner,
    )
    app_context.workflow_collaboration_service.upsert_workflow_participant(
        created.task_id,
        participant_agent_id="agent-b",
        role="reviewer",
        agent_principal=owner,
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=collaborator)

    assert bundle.workflow_review_controls is None


def test_review_bundle_builder_suggests_pin_and_revise_for_owner_controls(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    _seed_agent_memory(
        app_context,
        memory_id="mem-pinned",
        agent_id="agent-a",
        summary_text="Geometry layout guidance for centered diagrams.",
    )
    _seed_agent_memory(
        app_context,
        memory_id="mem-contrast",
        agent_id="agent-a",
        summary_text="Use strong contrast and an opening motion beat for educational explainers.",
    )
    created = app_context.task_service.create_video_task(
        prompt="draw a circle explainer with strong contrast",
        session_id="session-1",
        memory_ids=["mem-pinned"],
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

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.workflow_review_controls is not None
    assert bundle.workflow_review_controls.suggested_next_actions is not None
    assert bundle.workflow_review_controls.suggested_next_actions.primary.action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.suggested_next_actions.primary.payload["pin_workflow_memory_ids"] == [
        "mem-contrast"
    ]
    assert bundle.workflow_review_controls.suggested_next_actions.primary.payload["review_decision"]["decision"] == "revise"
    assert bundle.workflow_review_controls.available_actions is not None
    pin_and_revise_card = [
        item for item in bundle.workflow_review_controls.available_actions.items if item.action_id == "pin_and_revise"
    ][0]
    assert pin_and_revise_card.is_primary is True
    assert pin_and_revise_card.blocked is False
    assert pin_and_revise_card.button_label == "Pin memory and revise"
    assert pin_and_revise_card.action_family == "combined"
    assert pin_and_revise_card.payload["pin_workflow_memory_ids"] == ["mem-contrast"]
    assert pin_and_revise_card.intent.review_decision == "revise"
    assert pin_and_revise_card.intent.mutates_workflow_memory is True
    assert pin_and_revise_card.intent.workflow_memory_change is not None
    assert pin_and_revise_card.intent.workflow_memory_change.pin_memory_ids == ["mem-contrast"]
    assert pin_and_revise_card.intent.workflow_memory_change.pin_count == 1
    assert pin_and_revise_card.intent.workflow_memory_change.unpin_count == 0
    blocked_accept = [
        item for item in bundle.workflow_review_controls.suggested_next_actions.alternatives if item.action_id == "accept"
    ][0]
    assert blocked_accept.blocked is True
    assert "task_not_completed" in blocked_accept.reasons
    blocked_accept_card = [
        item for item in bundle.workflow_review_controls.available_actions.items if item.action_id == "accept"
    ][0]
    assert blocked_accept_card.is_primary is False
    assert blocked_accept_card.blocked is True
    assert blocked_accept_card.action_family == "review_decision"
    assert "task_not_completed" in blocked_accept_card.reasons
    assert blocked_accept_card.intent.review_decision == "accept"
    assert blocked_accept_card.intent.mutates_workflow_memory is False
    assert blocked_accept_card.intent.workflow_memory_change is None
    assert bundle.workflow_review_controls.status_summary is not None
    assert bundle.workflow_review_controls.status_summary.recommended_action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.status_summary.acceptance_ready is False
    assert "task_not_completed" in bundle.workflow_review_controls.status_summary.acceptance_blockers
    assert bundle.workflow_review_controls.status_summary.pinned_memory_count == 1
    assert bundle.workflow_review_controls.status_summary.pending_memory_recommendation_count == 1
    assert bundle.workflow_review_controls.status_summary.has_pending_memory_updates is True
    assert bundle.workflow_review_controls.action_sections is not None
    assert [section.section_id for section in bundle.workflow_review_controls.action_sections.items] == [
        "recommended",
        "available",
        "blocked",
    ]
    assert bundle.workflow_review_controls.action_sections.items[0].items[0].action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.action_sections.items[0].items[0].action_family == "combined"
    assert bundle.workflow_review_controls.action_sections.items[1].items[0].action_id == "revise"
    assert bundle.workflow_review_controls.action_sections.items[1].items[0].action_family == "review_decision"
    assert bundle.workflow_review_controls.action_sections.items[2].items[0].action_id == "accept"
    assert bundle.workflow_review_controls.action_sections.items[2].items[0].action_family == "review_decision"
    assert bundle.workflow_review_controls.panel_header is not None
    assert bundle.workflow_review_controls.panel_header.tone == "attention"
    assert "Pin suggested workflow memory" in bundle.workflow_review_controls.panel_header.summary
    badge_values = {badge.badge_id: badge.value for badge in bundle.workflow_review_controls.panel_header.badges}
    assert badge_values["recommended_action"] == "pin_and_revise"
    assert badge_values["pending_memory"] == "1"
    assert badge_values["acceptance_blockers"] == "1"
    assert bundle.workflow_review_controls.panel_header.highlighted_event is None
    assert bundle.workflow_review_controls.applied_action_feedback is None
    assert bundle.workflow_review_controls.render_contract is not None
    assert bundle.workflow_review_controls.render_contract.panel_tone == "attention"
    assert bundle.workflow_review_controls.render_contract.display_priority == "high"
    assert bundle.workflow_review_controls.render_contract.default_focus_section_id == "recommended"
    assert bundle.workflow_review_controls.render_contract.default_expanded_section_ids == ["recommended", "blocked"]
    assert bundle.workflow_review_controls.render_contract.badge_order == [
        "recommended_action",
        "pending_memory",
        "acceptance_blockers",
    ]
    assert bundle.workflow_review_controls.render_contract.sticky_primary_action_emphasis == "strong"
    section_presentations = {
        item.section_id: item for item in bundle.workflow_review_controls.render_contract.section_presentations
    }
    assert section_presentations["recommended"].tone == "accent"
    assert section_presentations["recommended"].collapsible is False
    assert section_presentations["available"].tone == "neutral"
    assert section_presentations["available"].collapsible is True
    assert bundle.workflow_review_controls.render_contract.sticky_primary_action_id == "pin_and_revise"
    assert bundle.workflow_review_controls.render_contract.applied_feedback_dismissible is False


def test_review_bundle_builder_suggests_accept_when_task_is_ready(tmp_path: Path) -> None:
    app_context = _with_temporary_mcp_shim(lambda: _create_app_context(_build_required_auth_settings(tmp_path)))
    _seed_required_agent(app_context, "agent-a", "agent-a-secret")
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        agent_principal=owner,
    )
    task = app_context.store.get_task(created.task_id)
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    task.delivery_status = "delivered"
    task.resolved_task_id = task.task_id
    app_context.store.update_task(task)

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        collaboration_service=app_context.workflow_collaboration_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(task_id=created.task_id, agent_principal=owner)

    assert bundle.workflow_review_controls is not None
    assert bundle.workflow_review_controls.suggested_next_actions is not None
    assert bundle.workflow_review_controls.suggested_next_actions.primary.action_id == "accept"
    assert bundle.workflow_review_controls.suggested_next_actions.primary.blocked is False
    assert bundle.workflow_review_controls.suggested_next_actions.primary.payload["review_decision"]["decision"] == "accept"
    assert bundle.workflow_review_controls.available_actions is not None
    accept_card = [item for item in bundle.workflow_review_controls.available_actions.items if item.action_id == "accept"][0]
    assert accept_card.is_primary is True
    assert accept_card.blocked is False
    assert accept_card.button_label == "Accept result"
    assert accept_card.payload["review_decision"]["decision"] == "accept"
    assert accept_card.intent.review_decision == "accept"
    assert accept_card.intent.mutates_workflow_memory is False
    assert accept_card.intent.workflow_memory_change is None
    assert bundle.workflow_review_controls.status_summary is not None
    assert bundle.workflow_review_controls.status_summary.recommended_action_id == "accept"
    assert bundle.workflow_review_controls.status_summary.acceptance_ready is True
    assert bundle.workflow_review_controls.status_summary.acceptance_blockers == []
    assert bundle.workflow_review_controls.status_summary.pinned_memory_count == 0
    assert bundle.workflow_review_controls.status_summary.pending_memory_recommendation_count == 0
    assert bundle.workflow_review_controls.status_summary.has_pending_memory_updates is False
    assert bundle.workflow_review_controls.action_sections is not None
    assert [section.section_id for section in bundle.workflow_review_controls.action_sections.items] == ["recommended"]
    assert bundle.workflow_review_controls.action_sections.items[0].items[0].action_id == "accept"
    assert bundle.workflow_review_controls.action_sections.items[0].items[0].action_family == "review_decision"
    assert bundle.workflow_review_controls.panel_header is not None
    assert bundle.workflow_review_controls.panel_header.tone == "ready"
    assert "ready to accept" in bundle.workflow_review_controls.panel_header.summary
    badge_values = {badge.badge_id: badge.value for badge in bundle.workflow_review_controls.panel_header.badges}
    assert badge_values["recommended_action"] == "accept"
    assert bundle.workflow_review_controls.panel_header.highlighted_event is None
    assert bundle.workflow_review_controls.applied_action_feedback is None
    assert bundle.workflow_review_controls.render_contract is not None
    assert bundle.workflow_review_controls.render_contract.panel_tone == "ready"
    assert bundle.workflow_review_controls.render_contract.display_priority == "normal"
    assert bundle.workflow_review_controls.render_contract.section_order == ["recommended"]
    assert bundle.workflow_review_controls.render_contract.default_focus_section_id == "recommended"
    assert bundle.workflow_review_controls.render_contract.default_expanded_section_ids == ["recommended"]
    assert bundle.workflow_review_controls.render_contract.badge_order == ["recommended_action"]
    assert bundle.workflow_review_controls.render_contract.sticky_primary_action_emphasis == "normal"
    assert bundle.workflow_review_controls.render_contract.section_presentations[0].section_id == "recommended"
    assert bundle.workflow_review_controls.render_contract.section_presentations[0].tone == "accent"
    assert bundle.workflow_review_controls.render_contract.section_presentations[0].collapsible is False
    assert bundle.workflow_review_controls.render_contract.sticky_primary_action_id == "accept"
    assert bundle.workflow_review_controls.render_contract.applied_feedback_dismissible is False
