from video_agent.config import Settings
from video_agent.domain.review_workflow_models import ReviewBundle, ReviewDecision
from video_agent.application.workflow_loop_policy import WorkflowLoopPolicy


def test_workflow_loop_policy_accept_requires_completed_when_enabled() -> None:
    policy = WorkflowLoopPolicy(Settings(multi_agent_workflow_require_completed_for_accept=True))
    bundle = ReviewBundle(
        task_id="task-1",
        root_task_id="task-1",
        status="failed",
        phase="failed",
    )
    decision = ReviewDecision(decision="accept", summary="looks good")

    assert policy.choose_action(bundle=bundle, review_decision=decision) == "escalate"


def test_workflow_loop_policy_maps_repair_to_revise() -> None:
    policy = WorkflowLoopPolicy(Settings(multi_agent_workflow_max_child_attempts=3))
    bundle = ReviewBundle(
        task_id="task-1",
        root_task_id="task-1",
        status="failed",
        phase="failed",
        child_attempt_count=0,
    )
    decision = ReviewDecision(
        decision="repair",
        summary="fix it",
        feedback="repair the output",
    )

    assert policy.choose_action(bundle=bundle, review_decision=decision) == "revise"


def test_workflow_loop_policy_escalates_when_budget_exhausted() -> None:
    policy = WorkflowLoopPolicy(Settings(multi_agent_workflow_max_child_attempts=1))
    bundle = ReviewBundle(
        task_id="task-1",
        root_task_id="task-1",
        status="failed",
        phase="failed",
        child_attempt_count=1,
    )
    decision = ReviewDecision(
        decision="revise",
        summary="try again",
        feedback="adjust style",
    )

    assert policy.choose_action(bundle=bundle, review_decision=decision) == "escalate"


def test_workflow_loop_policy_returns_decision_when_allowed() -> None:
    policy = WorkflowLoopPolicy(Settings(multi_agent_workflow_max_child_attempts=3))
    bundle = ReviewBundle(
        task_id="task-1",
        root_task_id="task-1",
        status="completed",
        phase="completed",
        child_attempt_count=0,
    )
    decision = ReviewDecision(decision="retry", summary="retry once")

    assert policy.choose_action(bundle=bundle, review_decision=decision) == "retry"
