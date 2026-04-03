from pathlib import Path
import sys
import types
from collections.abc import Callable

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
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


def _create_http_api(settings: Settings):
    def _load():
        from video_agent.server.http_api import create_http_api

        return create_http_api(settings)

    return _with_temporary_mcp_shim(_load)


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="optional",
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


def _seed_agent(client: TestClient, agent_id: str, secret: str) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id=agent_id,
            name=agent_id,
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def _login(client: TestClient, secret: str) -> str:
    response = client.post("/api/sessions", json={"agent_token": secret})
    assert response.status_code == 200
    return response.json()["session_token"]


def test_http_video_threads_api_creates_surface_and_revision(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_settings(tmp_path)))

    created = client.post(
        "/api/video-threads",
        json={
            "title": "Circle explainer",
            "prompt": "draw a circle",
            "owner_agent_id": "owner",
        },
    )
    assert created.status_code == 200
    thread_id = created.json()["thread"]["thread_id"]
    iteration_id = created.json()["iteration"]["iteration_id"]
    assert created.json()["created_task"]["task_id"]

    thread = client.get(f"/api/video-threads/{thread_id}")
    assert thread.status_code == 200
    assert thread.json()["thread_id"] == thread_id

    surface = client.get(f"/api/video-threads/{thread_id}/surface")
    assert surface.status_code == 200
    assert surface.json()["thread_header"]["thread_id"] == thread_id
    assert surface.json()["current_focus"]["current_iteration_id"] == iteration_id
    assert surface.json()["participants"]["items"][0]["role"] == "owner"

    revised = client.post(
        f"/api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision",
        json={
            "summary": "Slow the opener and make the title entrance more deliberate.",
            "preserve_working_parts": True,
        },
    )
    assert revised.status_code == 200
    assert revised.json()["thread"]["thread_id"] == thread_id
    assert revised.json()["created_task"]["task_id"]
    assert revised.json()["iteration"]["parent_iteration_id"] == iteration_id


def test_http_video_threads_api_supports_discussion_explanation_and_result_selection(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_settings(tmp_path)))

    created = client.post(
        "/api/video-threads",
        json={
            "title": "Circle explainer",
            "prompt": "draw a circle",
            "owner_agent_id": "owner",
        },
    )
    assert created.status_code == 200
    thread_id = created.json()["thread"]["thread_id"]
    iteration_id = created.json()["iteration"]["iteration_id"]
    app_context = client.app.state.app_context
    app_context.video_thread_service.upsert_participant(
        thread_id=thread_id,
        participant_id="planner-1",
        participant_type="agent",
        agent_id="planner-1",
        role="planner",
        display_name="Planner",
    )

    turn = client.post(
        f"/api/video-threads/{thread_id}/turns",
        json={
            "iteration_id": iteration_id,
            "title": "Why this pacing?",
            "summary": "Explain why the opener starts slowly before the title card lands.",
            "addressed_participant_id": "planner-1",
            "reply_to_turn_id": "turn-root",
            "related_result_id": "result-0",
        },
    )
    assert turn.status_code == 200
    assert turn.json()["turn"]["turn_type"] == "owner_request"
    assert turn.json()["turn"]["intent_type"] == "discuss"
    assert turn.json()["turn"]["addressed_participant_id"] == "planner-1"
    assert turn.json()["turn"]["addressed_agent_id"] == "planner-1"
    assert turn.json()["turn"]["reply_to_turn_id"] == "turn-root"
    assert turn.json()["turn"]["related_result_id"] == "result-0"

    explanation = client.post(
        f"/api/video-threads/{thread_id}/iterations/{iteration_id}/request-explanation",
        json={"summary": "Why did you choose this slower opening?"},
    )
    assert explanation.status_code == 200
    assert explanation.json()["owner_turn"]["turn_type"] == "owner_request"
    assert explanation.json()["owner_turn"]["intent_type"] == "request_explanation"
    assert explanation.json()["agent_turn"]["turn_type"] == "agent_explanation"
    assert explanation.json()["agent_turn"]["intent_type"] == "request_explanation"
    assert explanation.json()["agent_turn"]["reply_to_turn_id"] == explanation.json()["owner_turn"]["turn_id"]

    origin_result = app_context.video_iteration_service.register_result(
        thread_id=thread_id,
        iteration_id=iteration_id,
        source_task_id=created.json()["created_task"]["task_id"],
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    selected_origin = client.post(
        f"/api/video-threads/{thread_id}/iterations/{iteration_id}/select-result",
        json={"result_id": origin_result.result_id},
    )
    assert selected_origin.status_code == 200

    revised = client.post(
        f"/api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision",
        json={
            "summary": "Slow the opener and make the title entrance more deliberate.",
            "preserve_working_parts": True,
        },
    )
    assert revised.status_code == 200
    revised_iteration_id = revised.json()["iteration"]["iteration_id"]
    assert revised.json()["iteration"]["responsible_role"] == "planner"
    assert revised.json()["iteration"]["responsible_agent_id"] == "planner-1"
    revised_task_snapshot = app_context.task_service.get_video_task(revised.json()["created_task"]["task_id"]).model_dump(
        mode="json"
    )
    assert revised_task_snapshot["target_participant_id"] == "planner-1"
    assert revised_task_snapshot["target_agent_id"] == "planner-1"
    assert revised_task_snapshot["target_agent_role"] == "planner"

    result = app_context.video_iteration_service.register_result(
        thread_id=thread_id,
        iteration_id=revised_iteration_id,
        source_task_id=revised.json()["created_task"]["task_id"],
        status="ready",
        result_summary="Selected cut with a slower title entrance.",
    )
    result.video_resource = f"video-task://{revised.json()['created_task']['task_id']}/artifacts/final.mp4"
    app_context.store.upsert_video_result(result)

    selected = client.post(
        f"/api/video-threads/{thread_id}/iterations/{revised_iteration_id}/select-result",
        json={"result_id": result.result_id},
    )
    assert selected.status_code == 200
    assert selected.json()["thread"]["selected_result_id"] == result.result_id

    surface = client.get(f"/api/video-threads/{thread_id}/surface")
    assert surface.status_code == 200
    assert surface.json()["thread_header"]["selected_result_id"] == result.result_id
    assert surface.json()["iteration_compare"]["previous_iteration_id"] == iteration_id
    assert surface.json()["iteration_compare"]["current_iteration_id"] == revised_iteration_id
    assert surface.json()["iteration_compare"]["previous_result_id"] == origin_result.result_id
    assert surface.json()["iteration_compare"]["current_result_id"] == result.result_id
    assert surface.json()["iteration_compare"]["change_summary"] == "Selected cut with a slower title entrance."
    assert "Slow the opener and make the title entrance more deliberate." in surface.json()["iteration_compare"][
        "rationale_shift_summary"
    ]
    assert surface.json()["iteration_compare"]["continuity_status"] == "preserved"
    assert surface.json()["render_contract"]["sticky_primary_action_id"] == "request_revision"
    assert surface.json()["render_contract"]["sticky_primary_action_emphasis"] == "strong"
    assert surface.json()["render_contract"]["badge_order"] == [
        "owner_action_required",
        "selected_result",
        "expected_agent_role",
    ]
    recent_titles = [item["title"] for item in surface.json()["conversation"]["turns"]]
    assert "Why this pacing?" in recent_titles
    assert "Why did you choose this slower opening?" in recent_titles
    assert "Visible explanation" in recent_titles
    assert surface.json()["current_focus"]["current_result_author_role"] == "planner"
    assert surface.json()["current_focus"]["current_result_selection_reason"]
    assert surface.json()["selection_summary"]["selected_result_id"] == result.result_id
    assert surface.json()["latest_explanation"]["summary"]
    assert surface.json()["authorship"]["primary_agent_role"] == "planner"
    assert surface.json()["decision_notes"]["title"] == "Decision Notes"
    assert surface.json()["decision_notes"]["items"][0]["note_kind"] == "selection_rationale"
    assert surface.json()["decision_notes"]["items"][1]["note_kind"] == "agent_explanation"
    assert surface.json()["composer"]["target"]["iteration_id"] == revised_iteration_id
    assert surface.json()["composer"]["target"]["result_id"] == result.result_id
    assert surface.json()["composer"]["target"]["addressed_participant_id"] == "planner-1"
    assert surface.json()["composer"]["target"]["addressed_agent_id"] == "planner-1"
    assert surface.json()["composer"]["target"]["addressed_display_name"] == "Planner"
    assert surface.json()["composer"]["target"]["agent_role"] == "planner"
    assert surface.json()["discussion_runtime"]["title"] == "Discussion Runtime"
    assert surface.json()["discussion_runtime"]["active_iteration_id"] == revised_iteration_id
    assert surface.json()["discussion_runtime"]["active_discussion_group_id"] == (
        surface.json()["discussion_groups"]["groups"][0]["group_id"]
    )
    assert surface.json()["discussion_runtime"]["continuity_scope"] == "iteration"
    assert surface.json()["discussion_runtime"]["reply_policy"] == "continue_thread"
    assert surface.json()["discussion_runtime"]["default_intent_type"] == "discuss"
    assert surface.json()["discussion_runtime"]["default_reply_to_turn_id"] == (
        surface.json()["discussion_groups"]["groups"][0]["prompt_turn_id"]
    )
    assert surface.json()["discussion_runtime"]["default_related_result_id"] == result.result_id
    assert surface.json()["discussion_runtime"]["addressed_participant_id"] == "planner-1"
    assert surface.json()["discussion_runtime"]["addressed_agent_id"] == "planner-1"
    assert surface.json()["discussion_runtime"]["addressed_display_name"] == "Planner"
    assert surface.json()["discussion_runtime"]["suggested_follow_up_modes"] == [
        "ask_why",
        "request_change",
        "preserve_direction",
        "branch_revision",
    ]
    assert surface.json()["artifact_lineage"]["title"] == "Artifact Lineage"
    assert surface.json()["artifact_lineage"]["selected_result_id"] == result.result_id
    assert [item["from_result_id"] for item in surface.json()["artifact_lineage"]["items"]] == [
        None,
        origin_result.result_id,
    ]
    assert [item["to_result_id"] for item in surface.json()["artifact_lineage"]["items"]] == [
        origin_result.result_id,
        result.result_id,
    ]
    assert surface.json()["artifact_lineage"]["items"][1]["status"] == "selected"
    assert surface.json()["rationale_snapshots"]["title"] == "Rationale Snapshots"
    assert surface.json()["rationale_snapshots"]["current_iteration_id"] == revised_iteration_id
    assert [item["snapshot_kind"] for item in surface.json()["rationale_snapshots"]["items"]] == [
        "agent_explanation",
        "selection_rationale",
    ]
    assert surface.json()["iteration_detail"]["selected_iteration_id"] == revised_iteration_id
    assert surface.json()["iteration_detail"]["resource_uri"] == (
        f"video-thread://{thread_id}/iterations/{revised_iteration_id}.json"
    )

    iteration = client.get(f"/api/video-threads/{thread_id}/iterations/{revised_iteration_id}")
    assert iteration.status_code == 200
    assert iteration.json()["iteration_id"] == revised_iteration_id
    assert iteration.json()["summary"]
    assert iteration.json()["composer_target"]["iteration_id"] == revised_iteration_id
    assert iteration.json()["composer_target"]["result_id"] == result.result_id
    assert iteration.json()["composer_target"]["addressed_participant_id"] == "planner-1"
    assert iteration.json()["composer_target"]["addressed_agent_id"] == "planner-1"
    assert iteration.json()["composer_target"]["addressed_display_name"] == "Planner"
    assert iteration.json()["execution_summary"]["title"] == "Execution Summary"
    assert iteration.json()["execution_summary"]["summary"] == (
        "Planner has not started a tracked task yet, but the iteration is anchored to this agent."
    )
    assert iteration.json()["execution_summary"]["task_id"] is None
    assert iteration.json()["execution_summary"]["run_id"] is None
    assert iteration.json()["execution_summary"]["status"] == "pending"
    assert iteration.json()["execution_summary"]["phase"] is None
    assert iteration.json()["execution_summary"]["agent_id"] == "planner-1"
    assert iteration.json()["execution_summary"]["agent_display_name"] == "Planner"
    assert iteration.json()["execution_summary"]["agent_role"] == "planner"
    assert iteration.json()["execution_summary"]["result_id"] == result.result_id
    assert iteration.json()["execution_summary"]["discussion_group_id"] == (
        f"group-{iteration.json()['turns'][0]['turn_id']}"
    )
    assert iteration.json()["execution_summary"]["reply_to_turn_id"] == iteration.json()["turns"][0]["turn_id"]
    assert iteration.json()["execution_summary"]["latest_owner_turn_id"] == iteration.json()["turns"][0]["turn_id"]
    assert iteration.json()["execution_summary"]["latest_agent_turn_id"] is None
    assert iteration.json()["execution_summary"]["is_active"] is False
    assert iteration.json()["runs"] == []
    assert iteration.json()["turns"][0]["intent_type"] == "request_revision"
    assert iteration.json()["results"][0]["result_id"] == result.result_id
    assert surface.json()["production_journal"]["title"] == "Production Journal"
    assert surface.json()["production_journal"]["entries"][-1]["entry_kind"] == "result"
    assert surface.json()["production_journal"]["entries"][-1]["resource_refs"] == [
        f"video-task://{revised.json()['created_task']['task_id']}/artifacts/final.mp4"
    ]
    assert any(
        group["status"] == "answered" and group["prompt_intent_type"] == "request_explanation"
        for group in surface.json()["discussion_groups"]["groups"]
    )
    assert any(
        any(reply["turn_id"] == explanation.json()["agent_turn"]["turn_id"] for reply in group["replies"])
        for group in surface.json()["discussion_groups"]["groups"]
    )
    assert [item["card_type"] for item in surface.json()["history"]["cards"]] == [
        "agent_explanation",
        "result_selection",
        "owner_request",
    ]
    assert surface.json()["history"]["cards"][0]["actor_role"] == "planner"
    assert surface.json()["history"]["cards"][0]["intent_type"] == "request_explanation"
    assert surface.json()["history"]["cards"][0]["reply_to_turn_id"] == explanation.json()["owner_turn"]["turn_id"]
    assert any(
        item["panel_id"] == "history" and item["default_open"]
        for item in surface.json()["render_contract"]["panel_presentations"]
    )
    assert "artifact_lineage" in surface.json()["render_contract"]["panel_order"]
    assert "rationale_snapshots" in surface.json()["render_contract"]["panel_order"]
    assert surface.json()["next_recommended_move"]["recommended_action_id"] == "request_revision"


def test_http_video_threads_api_manages_thread_participants(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_settings(tmp_path)))

    created = client.post(
        "/api/video-threads",
        json={
            "title": "Circle explainer",
            "prompt": "draw a circle",
            "owner_agent_id": "owner",
        },
    )
    assert created.status_code == 200
    thread_id = created.json()["thread"]["thread_id"]

    listed = client.get(f"/api/video-threads/{thread_id}/participants")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["role"] == "owner"

    upserted = client.post(
        f"/api/video-threads/{thread_id}/participants",
        json={
            "participant_id": "reviewer-1",
            "participant_type": "agent",
            "agent_id": "reviewer-1",
            "role": "reviewer",
            "display_name": "Reviewer",
            "capabilities": ["review_bundle:read"],
        },
    )
    assert upserted.status_code == 200
    assert upserted.json()["participant"]["participant_id"] == "reviewer-1"

    removed = client.delete(f"/api/video-threads/{thread_id}/participants/reviewer-1")
    assert removed.status_code == 200
    assert removed.json()["removed"] is True


def test_http_non_owner_cannot_manage_thread_participants(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_required_auth_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    owner_token = _login(client, "agent-a-secret")
    intruder_token = _login(client, "agent-b-secret")

    created = client.post(
        "/api/video-threads",
        json={
            "title": "Circle explainer",
            "prompt": "draw a circle",
            "owner_agent_id": "agent-a",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200
    thread_id = created.json()["thread"]["thread_id"]

    listed = client.get(
        f"/api/video-threads/{thread_id}/participants",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    upserted = client.post(
        f"/api/video-threads/{thread_id}/participants",
        json={
            "participant_id": "reviewer-1",
            "participant_type": "agent",
            "agent_id": "agent-b",
            "role": "reviewer",
            "display_name": "Reviewer",
            "capabilities": ["review_bundle:read"],
        },
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    removed = client.delete(
        f"/api/video-threads/{thread_id}/participants/owner",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert listed.status_code == 200
    assert listed.json()["items"][0]["role"] == "owner"
    assert upserted.status_code == 403
    assert upserted.json()["detail"] == "agent_access_denied"
    assert removed.status_code == 403
    assert removed.json()["detail"] == "agent_access_denied"
