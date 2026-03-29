# Supervised Multi-Agent Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a supervised multi-agent review workflow that lets external or logical reviewer agents fetch a stable review bundle and submit a structured decision that the system can turn into `accept`, `revise`, or `retry` actions safely.

**Architecture:** Keep the current single-owner task model intact and add a thin orchestration layer above `TaskService`. That layer should expose two core capabilities: `get_review_bundle(task_id)` for read-only specialist agents and `apply_review_decision(task_id, decision)` for the orchestrator that converts review output into existing task mutations. The implementation should reuse current lineage, validation, failure contract, and session memory behavior rather than inventing a new executor.

**Tech Stack:** Python, Pydantic, FastAPI, FastMCP, existing SQLite-backed store, pytest

---

## Pre-flight

Read these files before touching code:

- `docs/plans/2026-03-28-multi-agent-workflow-design.md`
- `src/video_agent/application/task_service.py`
- `src/video_agent/server/app.py`
- `src/video_agent/server/mcp_tools.py`
- `src/video_agent/server/http_api.py`
- `tests/integration/test_mcp_tools.py`
- `tests/integration/test_http_task_api.py`

Phase 1 scope is intentionally narrow:

1. Expose review bundles to reviewer agents.
2. Accept structured review decisions from an orchestrator.
3. Route those decisions into existing `revise_video_task` and `retry_video_task` flows.
4. Enforce a simple child-attempt budget.

Phase 1 explicitly does **not** implement true cross-agent shared task ownership.

### Task 1: Review Workflow Models and Config

**Files:**
- Create: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/config.py:10-85`
- Modify: `src/video_agent/server/main.py:87-136`
- Test: `tests/unit/domain/test_review_workflow_models.py`
- Test: `tests/unit/test_settings.py:15-84`

**Step 1: Write the failing tests**

```python
import pytest
from pydantic import ValidationError

from video_agent.config import Settings
from video_agent.domain.review_workflow_models import ReviewDecision


def test_review_decision_requires_feedback_for_revision_actions() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(
            decision="revise",
            summary="Needs another pass",
        )


def test_settings_expose_multi_agent_workflow_defaults() -> None:
    settings = Settings()

    assert settings.multi_agent_workflow_enabled is False
    assert settings.multi_agent_workflow_max_child_attempts == 3
    assert settings.multi_agent_workflow_require_completed_for_accept is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_review_workflow_models.py tests/unit/test_settings.py -q`
Expected: FAIL with import errors or missing settings fields such as `multi_agent_workflow_enabled`.

**Step 3: Write minimal implementation**

```python
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReviewIssue(BaseModel):
    code: str
    severity: Literal["low", "medium", "high"]
    evidence: str
    action: str


class ReviewDecision(BaseModel):
    decision: Literal["accept", "revise", "retry", "repair", "escalate"]
    summary: str
    preserve_working_parts: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    issues: list[ReviewIssue] = Field(default_factory=list)
    feedback: str | None = None
    stop_reason: str | None = None

    @model_validator(mode="after")
    def validate_feedback_requirements(self) -> "ReviewDecision":
        if self.decision in {"revise", "repair"} and not (self.feedback or "").strip():
            raise ValueError("feedback is required for revise or repair decisions")
        return self
```

Add the following settings and env wiring:

```python
multi_agent_workflow_enabled: bool = False
multi_agent_workflow_max_child_attempts: int = 3
multi_agent_workflow_require_completed_for_accept: bool = True
```

And in `build_settings(...)`:

```python
multi_agent_workflow_enabled=_env_bool("EASY_MANIM_MULTI_AGENT_WORKFLOW_ENABLED", False),
multi_agent_workflow_max_child_attempts=_env_int("EASY_MANIM_MULTI_AGENT_WORKFLOW_MAX_CHILD_ATTEMPTS", 3),
multi_agent_workflow_require_completed_for_accept=_env_bool(
    "EASY_MANIM_MULTI_AGENT_WORKFLOW_REQUIRE_COMPLETED_FOR_ACCEPT",
    True,
),
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/test_review_workflow_models.py tests/unit/test_settings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/domain/test_review_workflow_models.py tests/unit/test_settings.py src/video_agent/domain/review_workflow_models.py src/video_agent/config.py src/video_agent/server/main.py
git commit -m "feat: add review workflow models and settings"
```

### Task 2: Review Bundle Builder

**Files:**
- Create: `src/video_agent/application/review_bundle_builder.py`
- Create: `tests/integration/test_review_bundle_builder.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`

**Step 1: Write the failing test**

```python
from video_agent.server.app import create_app_context
from video_agent.application.review_bundle_builder import ReviewBundleBuilder


def test_review_bundle_builder_collects_task_result_and_memory(tmp_path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    builder = ReviewBundleBuilder(
        task_service=app_context.task_service,
        store=app_context.store,
        session_memory_service=app_context.session_memory_service,
    )
    bundle = builder.build(
        task_id=created.task_id,
        agent_principal=None,
    )

    assert bundle.task_id == created.task_id
    assert bundle.root_task_id == created.task_id
    assert bundle.child_attempt_count == 0
    assert bundle.session_memory_summary is not None
```

Also add an auth-scope test:

```python
def test_review_bundle_builder_respects_agent_scoping(tmp_path) -> None:
    app_context = create_app_context(_build_required_auth_settings(tmp_path))
    # seed two agents, create a task for agent-a, then assert agent-b gets PermissionError
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_review_bundle_builder.py -q`
Expected: FAIL because `review_bundle_builder` is missing and no bundle model exists yet.

**Step 3: Write minimal implementation**

Add `ReviewBundle` and `ReviewBundleArtifactRefs` to `src/video_agent/domain/review_workflow_models.py`, then implement:

```python
class ReviewBundleBuilder:
    def __init__(self, *, task_service, store, session_memory_service) -> None:
        self.task_service = task_service
        self.store = store
        self.session_memory_service = session_memory_service

    def build(self, *, task_id: str, agent_principal=None) -> ReviewBundle:
        snapshot = (
            self.task_service.get_video_task(task_id)
            if agent_principal is None
            else self.task_service.get_video_task_for_agent(task_id, agent_principal.agent_id)
        )
        result = (
            self.task_service.get_video_result(task_id)
            if agent_principal is None
            else self.task_service.get_video_result_for_agent(task_id, agent_principal.agent_id)
        )
        events = (
            self.task_service.get_task_events(task_id)
            if agent_principal is None
            else self.task_service.get_task_events_for_agent(task_id, agent_principal.agent_id)
        )
        task = self.store.get_task(task_id)
        session_summary = ""
        if task is not None and task.session_id is not None:
            session_summary = self.session_memory_service.summarize_session_memory(task.session_id).summary_text
        return ReviewBundle(
            task_id=snapshot.task_id,
            root_task_id=snapshot.root_task_id,
            attempt_count=snapshot.attempt_count,
            child_attempt_count=snapshot.artifact_summary["repair_children"],
            prompt=task.prompt if task is not None else "",
            feedback=task.feedback if task is not None else None,
            display_title=snapshot.display_title,
            status=snapshot.status,
            phase=snapshot.phase,
            latest_validation_summary=snapshot.latest_validation_summary,
            failure_contract=snapshot.failure_contract,
            task_events=events,
            session_memory_summary=session_summary or "",
            video_resource=result.video_resource,
            preview_frame_resources=result.preview_frame_resources,
            script_resource=result.script_resource,
            validation_report_resource=result.validation_report_resource,
        )
```

Use `max(0, self.store.count_lineage_tasks(snapshot.root_task_id) - 1)` for `child_attempt_count` instead of reading repair-only state.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_review_bundle_builder.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_review_bundle_builder.py src/video_agent/domain/review_workflow_models.py src/video_agent/application/review_bundle_builder.py
git commit -m "feat: add review bundle builder"
```

### Task 3: Workflow Policy and Service

**Files:**
- Create: `src/video_agent/application/workflow_loop_policy.py`
- Create: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/server/app.py:33-50`
- Modify: `src/video_agent/server/app.py:76-178`
- Test: `tests/unit/application/test_workflow_loop_policy.py`
- Test: `tests/integration/test_multi_agent_workflow_service.py`

**Step 1: Write the failing tests**

```python
from video_agent.domain.review_workflow_models import ReviewDecision


def test_workflow_service_routes_revision_decision_to_child_task(tmp_path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="revise",
            summary="Needs stronger visual emphasis",
            feedback="Make the circle blue and add a title card",
        ),
        session_id="session-1",
        agent_principal=None,
    )

    assert outcome.action == "revise"
    assert outcome.created_task_id is not None


def test_workflow_service_escalates_when_child_budget_is_exhausted(tmp_path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.multi_agent_workflow_enabled = True
    settings.multi_agent_workflow_max_child_attempts = 0
    app_context = create_app_context(settings)
    created = app_context.task_service.create_video_task(prompt="draw a circle")

    outcome = app_context.multi_agent_workflow_service.apply_review_decision(
        task_id=created.task_id,
        review_decision=ReviewDecision(
            decision="revise",
            summary="One more pass",
            feedback="Make it blue",
        ),
        session_id=None,
        agent_principal=None,
    )

    assert outcome.action == "escalate"
    assert outcome.created_task_id is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_workflow_loop_policy.py tests/integration/test_multi_agent_workflow_service.py -q`
Expected: FAIL because the new policy and service do not exist.

**Step 3: Write minimal implementation**

Policy:

```python
class WorkflowLoopPolicy:
    def __init__(self, settings) -> None:
        self.settings = settings

    def choose_action(self, *, bundle, review_decision) -> str:
        if review_decision.decision == "accept":
            if self.settings.multi_agent_workflow_require_completed_for_accept and bundle.status != "completed":
                return "escalate"
            return "accept"
        if bundle.child_attempt_count >= self.settings.multi_agent_workflow_max_child_attempts:
            return "escalate"
        if review_decision.decision == "repair":
            return "revise"
        return review_decision.decision
```

Service:

```python
class MultiAgentWorkflowService:
    def __init__(self, *, settings, bundle_builder, task_service, policy) -> None:
        self.settings = settings
        self.bundle_builder = bundle_builder
        self.task_service = task_service
        self.policy = policy

    def get_review_bundle(self, *, task_id: str, agent_principal=None):
        return self.bundle_builder.build(task_id=task_id, agent_principal=agent_principal)

    def apply_review_decision(self, *, task_id: str, review_decision, session_id=None, memory_ids=None, agent_principal=None):
        if not self.settings.multi_agent_workflow_enabled:
            raise AdmissionControlError("multi_agent_workflow_disabled", "Multi-agent workflow is disabled")

        bundle = self.get_review_bundle(task_id=task_id, agent_principal=agent_principal)
        action = self.policy.choose_action(bundle=bundle, review_decision=review_decision)
        if action == "accept":
            return ReviewDecisionOutcome(task_id=task_id, root_task_id=bundle.root_task_id, action="accept", created_task_id=None, reason="accepted")
        if action == "retry":
            created = self.task_service.retry_video_task(task_id, session_id=session_id, agent_principal=agent_principal)
            return ReviewDecisionOutcome(task_id=task_id, root_task_id=bundle.root_task_id, action="retry", created_task_id=created.task_id, reason="retry_created")
        if action == "revise":
            created = self.task_service.revise_video_task(
                task_id,
                feedback=review_decision.feedback or review_decision.summary,
                preserve_working_parts=review_decision.preserve_working_parts,
                session_id=session_id,
                memory_ids=memory_ids,
                agent_principal=agent_principal,
            )
            return ReviewDecisionOutcome(task_id=task_id, root_task_id=bundle.root_task_id, action="revise", created_task_id=created.task_id, reason="revision_created")
        return ReviewDecisionOutcome(task_id=task_id, root_task_id=bundle.root_task_id, action="escalate", created_task_id=None, reason="workflow_budget_exhausted")
```

Wire both components into `AppContext` so tests and APIs can call them directly.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_workflow_loop_policy.py tests/integration/test_multi_agent_workflow_service.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_workflow_loop_policy.py tests/integration/test_multi_agent_workflow_service.py src/video_agent/application/workflow_loop_policy.py src/video_agent/application/multi_agent_workflow_service.py src/video_agent/server/app.py
git commit -m "feat: add supervised multi-agent workflow service"
```

### Task 4: MCP Review Workflow Tools

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py:73-360`
- Modify: `src/video_agent/server/fastmcp_server.py:82-250`
- Create: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Modify: `tests/integration/test_fastmcp_server.py:79-202`

**Step 1: Write the failing tests**

```python
async def test_apply_review_decision_tool_creates_revision(tmp_path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.multi_agent_workflow_enabled = True
    mcp = create_mcp_server(settings)

    _, created = await mcp.call_tool("create_video_task", {"prompt": "draw a circle"})
    _, outcome = await mcp.call_tool(
        "apply_review_decision",
        {
            "task_id": created["task_id"],
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and center the title",
            },
        },
    )

    assert outcome["action"] == "revise"
    assert outcome["created_task_id"]
```

And update the tool registration smoke test:

```python
assert {"get_review_bundle", "apply_review_decision"} <= tool_names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_fastmcp_server.py -q`
Expected: FAIL because the tools are not registered.

**Step 3: Write minimal implementation**

In `mcp_tools.py`:

```python
def get_review_bundle_tool(context: AppContext, payload: dict[str, Any], *, agent_principal=None) -> dict[str, Any]:
    try:
        bundle = context.multi_agent_workflow_service.get_review_bundle(
            task_id=payload["task_id"],
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return bundle.model_dump(mode="json")


def apply_review_decision_tool(context: AppContext, payload: dict[str, Any], *, agent_principal=None) -> dict[str, Any]:
    try:
        decision = ReviewDecision.model_validate(payload["review_decision"])
        outcome = context.multi_agent_workflow_service.apply_review_decision(
            task_id=payload["task_id"],
            review_decision=decision,
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return outcome.model_dump(mode="json")
```

In `fastmcp_server.py` register:

```python
@mcp.tool(name="get_review_bundle")
def get_review_bundle(task_id: str, ctx: Context | None = None) -> dict[str, Any]:
    ...


@mcp.tool(name="apply_review_decision")
def apply_review_decision(task_id: str, review_decision: dict[str, Any], memory_ids: list[str] | None = None, ctx: Context | None = None) -> dict[str, Any]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_fastmcp_server.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_fastmcp_server.py src/video_agent/server/mcp_tools.py src/video_agent/server/fastmcp_server.py
git commit -m "feat: expose review workflow over mcp"
```

### Task 5: HTTP Review Workflow API

**Files:**
- Modify: `src/video_agent/server/http_api.py:37-80`
- Modify: `src/video_agent/server/http_api.py:159-821`
- Create: `tests/integration/test_http_multi_agent_workflow_api.py`

**Step 1: Write the failing tests**

```python
def test_http_review_bundle_and_decision_flow(tmp_path) -> None:
    settings = _build_http_task_settings(tmp_path)
    settings.multi_agent_workflow_enabled = True
    client = TestClient(create_http_api(settings))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    task_id = created.json()["task_id"]

    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert bundle.status_code == 200
    assert bundle.json()["task_id"] == task_id

    decision = client.post(
        f"/api/tasks/{task_id}/review-decision",
        json={
            "review_decision": {
                "decision": "revise",
                "summary": "Improve emphasis",
                "feedback": "Make it blue and add a title",
            }
        },
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert decision.status_code == 200
    assert decision.json()["action"] == "revise"
    assert decision.json()["created_task_id"]
```

Also add an agent-scope test where another agent gets `403`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
Expected: FAIL because the endpoints and request models do not exist.

**Step 3: Write minimal implementation**

Add request models near the existing task request models:

```python
class ReviewDecisionRequest(BaseModel):
    decision: str
    summary: str
    preserve_working_parts: bool = True
    confidence: float = 0.0
    issues: list[dict[str, Any]] = []
    feedback: str | None = None
    stop_reason: str | None = None


class ApplyReviewDecisionRequest(BaseModel):
    review_decision: ReviewDecisionRequest
    memory_ids: list[str] | None = None
```

Add endpoints:

```python
@app.get("/api/tasks/{task_id}/review-bundle")
def get_task_review_bundle(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
    bundle = context.multi_agent_workflow_service.get_review_bundle(
        task_id=task_id,
        agent_principal=resolved.agent_principal,
    )
    return _strip_internal_session_fields(bundle.model_dump(mode="json"))


@app.post("/api/tasks/{task_id}/review-decision")
def apply_task_review_decision(
    task_id: str,
    payload: ApplyReviewDecisionRequest,
    resolved: ResolvedAgentSession = Depends(resolve_agent_session),
) -> dict[str, Any]:
    decision = ReviewDecision.model_validate(payload.review_decision.model_dump(mode="json"))
    outcome = context.multi_agent_workflow_service.apply_review_decision(
        task_id=task_id,
        review_decision=decision,
        session_id=current_internal_session_id(resolved),
        memory_ids=payload.memory_ids,
        agent_principal=resolved.agent_principal,
    )
    return _strip_internal_session_fields(outcome.model_dump(mode="json"))
```

Map `AdmissionControlError("multi_agent_workflow_disabled", ...)` to `400` via `_tool_payload_or_http_error(...)` or a dedicated branch.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_http_multi_agent_workflow_api.py src/video_agent/server/http_api.py
git commit -m "feat: expose review workflow over http"
```

### Task 6: Documentation and Regression Verification

**Files:**
- Modify: `README.md:78-123`
- Modify: `docs/runbooks/agent-self-serve.md`
- Modify: `tests/integration/test_mcp_tools.py:103-226`
- Modify: `tests/integration/test_http_task_api.py:49-154`

**Step 1: Write the failing regression checks**

Add a small regression assertion to the existing task API tests confirming the new workflow endpoints do not leak cross-agent data and do not change existing task create/list/get behavior.

```python
def test_new_review_endpoints_do_not_change_existing_task_roundtrip(tmp_path) -> None:
    # Existing create/list/get/result behavior should still work unchanged.
```

**Step 2: Run targeted regression tests to verify at least one fails before docs and follow-up fixes**

Run: `pytest tests/integration/test_mcp_tools.py tests/integration/test_http_task_api.py -q`
Expected: either FAIL because helper imports or tool name assertions need updates, or PASS with no regressions after the earlier tasks. If already PASS, proceed without forcing a failure here.

**Step 3: Update docs**

Document:

1. the new MCP tools: `get_review_bundle`, `apply_review_decision`
2. the new HTTP endpoints: `GET /api/tasks/{task_id}/review-bundle`, `POST /api/tasks/{task_id}/review-decision`
3. the phase-1 workflow contract: reviewer agents are read-only and the orchestrator remains the task owner

Suggested README snippet:

```markdown
### Review-driven regeneration

Use `GET /api/tasks/{task_id}/review-bundle` to assemble a stable evaluation package for a reviewer agent.
After the reviewer returns a structured decision, send it to `POST /api/tasks/{task_id}/review-decision`.
The server will convert that decision into `accept`, `revise`, `retry`, or `escalate` without weakening task ownership rules.
```

**Step 4: Run the final verification set**

Run:

```bash
pytest \
  tests/unit/domain/test_review_workflow_models.py \
  tests/unit/application/test_workflow_loop_policy.py \
  tests/unit/test_settings.py \
  tests/integration/test_review_bundle_builder.py \
  tests/integration/test_multi_agent_workflow_service.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_fastmcp_server.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_http_task_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add README.md docs/runbooks/agent-self-serve.md tests/integration/test_mcp_tools.py tests/integration/test_http_task_api.py
git commit -m "docs: document supervised multi-agent workflow"
```

## Notes for the Implementer

1. Keep “repair” as targeted `revise` in phase 1. Do not introduce a second orchestration path that duplicates existing auto-repair logic.
2. Do not weaken `agent_id` ownership checks. Review agents should consume bundles, not mutate tasks directly.
3. Reuse `current_internal_session_id(...)` so revised child tasks stay attached to the same session memory scope.
4. Prefer returning structured `ReviewDecisionOutcome` results over throwing new exceptions for normal `accept` and `escalate` paths.
5. Keep the API shape JSON-friendly so an external agent runtime can adopt it later without another breaking change.
