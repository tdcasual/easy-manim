import importlib
import importlib.util

from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.models import VideoTask


MODULE_NAME = "video_agent.application.workflow_collaboration_memory"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def _memory_record(memory_id: str, summary_text: str) -> AgentMemoryRecord:
    return AgentMemoryRecord(
        memory_id=memory_id,
        agent_id="agent-a",
        source_session_id="session-a",
        summary_text=summary_text,
        summary_digest=f"digest-{memory_id}",
    )


def test_build_role_memory_context_shapes_case_memory_for_each_collaboration_role() -> None:
    module = _load_module()
    case_memory = {
        "delivery_invariants": ["Preserve core prompt intent: draw a circle."],
        "planner_notes": [{"generation_mode": "storyboard", "risk_level": "medium"}],
        "review_findings": [
            {
                "quality_gate_status": "needs_revision",
                "summary": "Preview opens too quietly.",
                "must_fix_issue_codes": ["contrast_low"],
            }
        ],
        "repair_constraints": [
            {
                "quality_gate_status": "needs_revision",
                "summary": "Need stronger opening beat.",
                "repair_strategy": "Increase contrast and add a visible motion beat.",
                "recovery_selected_action": "repair",
                "must_fix_issue_codes": ["contrast_low"],
            }
        ],
    }

    planner = module.build_role_memory_context(
        role="planner",
        shared_records=[],
        task_context_summary=None,
        case_memory=case_memory,
    )
    reviewer = module.build_role_memory_context(
        role="reviewer",
        shared_records=[],
        task_context_summary=None,
        case_memory=case_memory,
    )
    repairer = module.build_role_memory_context(
        role="repairer",
        shared_records=[],
        task_context_summary=None,
        case_memory=case_memory,
    )

    assert "Delivery invariant: Preserve core prompt intent: draw a circle." in planner.summary
    assert "Latest planner state: generation_mode=storyboard, risk_level=medium" in planner.summary
    assert "Latest review finding: quality_gate_status=needs_revision; Preview opens too quietly." in reviewer.summary
    assert "must_fix=contrast_low" in reviewer.summary
    assert "Latest repair constraint: quality_gate_status=needs_revision; Need stronger opening beat." in repairer.summary
    assert "Increase contrast and add a visible motion beat." in repairer.summary
    assert "recovery_selected_action=repair" in repairer.summary


def test_build_workflow_memory_context_prefers_shared_records_over_attached_task_context() -> None:
    module = _load_module()
    root_task = VideoTask(
        task_id="task-root",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle",
        selected_memory_ids=["mem-style"],
        persistent_memory_context_summary="Attached workflow memory from root",
    )
    child_task = VideoTask(
        task_id="task-child",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle",
        selected_memory_ids=["mem-style"],
        persistent_memory_context_summary="Attached workflow memory from child",
    )

    with_shared_records = module.build_workflow_memory_context(
        task=child_task,
        root_task=root_task,
        shared_records=[_memory_record("mem-style", "Prefer light backgrounds and visible motion.")],
        case_memory={},
    )
    without_shared_records = module.build_workflow_memory_context(
        task=child_task,
        root_task=root_task,
        shared_records=[],
        case_memory={},
    )

    assert with_shared_records.shared_memory_ids == ["mem-style"]
    assert [item.source for item in with_shared_records.planner.items] == ["persistent_memory"]
    assert "Attached workflow memory" not in with_shared_records.planner.summary
    assert [item.source for item in without_shared_records.planner.items] == ["task_context"]
    assert without_shared_records.planner.summary == "Attached workflow memory: Attached workflow memory from child"


def test_build_workflow_memory_context_uses_structured_persistent_memory_ids_when_legacy_fields_are_empty() -> None:
    module = _load_module()
    root_task = VideoTask(
        task_id="task-root",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle",
        task_memory_context={
            "persistent": {
                "memory_ids": ["mem-style"],
                "summary_text": "Prefer light backgrounds and visible motion.",
                "summary_digest": "digest-style",
                "items": [
                    {
                        "memory_id": "mem-style",
                        "summary_text": "Prefer light backgrounds and visible motion.",
                        "summary_digest": "digest-style",
                        "lineage_refs": ["video-task://task-root/task.json"],
                        "enhancement": {},
                    }
                ],
            }
        },
    )
    child_task = VideoTask(
        task_id="task-child",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle",
    )

    context = module.build_workflow_memory_context(
        task=child_task,
        root_task=root_task,
        shared_records=[_memory_record("mem-style", "Prefer light backgrounds and visible motion.")],
        case_memory={},
    )

    assert context.shared_memory_ids == ["mem-style"]


def test_resolve_task_memory_context_summary_prefers_structured_persistent_items() -> None:
    module = _load_module()
    root_task = VideoTask(
        task_id="task-root",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle",
    )
    child_task = VideoTask(
        task_id="task-child",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle",
        task_memory_context={
            "persistent": {
                "memory_ids": ["mem-style"],
                "summary_text": "Attached workflow memory from structured task context",
                "summary_digest": "digest-style",
                "items": [
                    {
                        "memory_id": "mem-style",
                        "summary_text": "Prefer light backgrounds and visible motion.",
                        "summary_digest": "digest-style",
                        "lineage_refs": ["video-task://task-root/task.json"],
                        "enhancement": {},
                    }
                ],
            }
        },
    )

    summary = module.resolve_task_memory_context_summary(task=child_task, root_task=root_task)

    assert summary == "Prefer light backgrounds and visible motion."


def test_build_workflow_memory_query_combines_prompt_review_summary_and_repair_strategy() -> None:
    module = _load_module()
    root_task = VideoTask(
        task_id="task-root",
        root_task_id="task-root",
        agent_id="agent-a",
        prompt="draw a circle explainer",
    )

    query = module.build_workflow_memory_query(
        root_task=root_task,
        case_memory={
            "review_findings": [{"summary": "Opening needs stronger contrast."}],
            "repair_constraints": [{"repair_strategy": "Add a visible opening motion beat."}],
        },
    )

    assert query == (
        "draw a circle explainer "
        "Opening needs stronger contrast. "
        "Add a visible opening motion beat."
    )
