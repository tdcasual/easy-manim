# OpenClaw Gateway Session Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish an OpenClaw-style gateway-owned session layer and route current MCP/HTTP entrypoints through it.

**Architecture:** Introduce a new `video_agent.openclaw` foundation package that centralizes session routing and reset policy. Existing task, workflow, and video-thread execution code stays intact in this phase; only session ownership moves from transport-specific helpers into one gateway session service.

**Tech Stack:** Python 3.13, Pydantic, pytest, FastMCP, FastAPI, SQLite-backed app context

---

### Task 1: Lock Session Routing Semantics With Failing Tests

**Files:**
- Create: `tests/unit/openclaw/test_gateway_sessions.py`
- Create: `src/video_agent/openclaw/__init__.py`
- Create: `src/video_agent/openclaw/gateway_sessions.py`

**Step 1: Write the failing test**

```python
def test_direct_message_routes_to_shared_session_by_default() -> None:
    service = GatewaySessionService(policy=GatewaySessionPolicy())
    first = service.resolve(route=GatewayRoute(source_kind="direct_message", source_id="peer-a"))
    second = service.resolve(route=GatewayRoute(source_kind="direct_message", source_id="peer-b"))
    assert first.session_id == second.session_id
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/openclaw/test_gateway_sessions.py -q`

Expected: FAIL because `video_agent.openclaw.gateway_sessions` does not exist yet.

**Step 3: Add more characterization tests**

Add tests for:

1. `per_peer` DM scope creates isolated sessions
2. group room routes isolate by room id
3. cron routes create fresh sessions
4. daily reset rotates a reused route into a new session
5. idle reset rotates inactive sessions

**Step 4: Re-run tests**

Run: `python -m pytest tests/unit/openclaw/test_gateway_sessions.py -q`

Expected: FAIL with import or missing implementation errors only.

### Task 2: Implement OpenClaw-Style Gateway Session Models

**Files:**
- Modify: `src/video_agent/openclaw/gateway_sessions.py`
- Modify: `src/video_agent/config.py`

**Step 1: Write minimal implementation**

Implement:

1. `GatewayRoute`
2. `GatewaySessionPolicy`
3. `GatewaySessionRecord`
4. `GatewaySessionService`

The service should:

1. compute a stable route key
2. support DM shared/per-peer policy
3. support isolated room sessions
4. create fresh cron sessions
5. apply daily and idle reset rules

**Step 2: Add config defaults**

Add settings fields for:

1. `gateway_session_dm_scope`
2. `gateway_session_daily_reset_hour_local`
3. `gateway_session_idle_reset_minutes`

**Step 3: Run tests**

Run: `python -m pytest tests/unit/openclaw/test_gateway_sessions.py -q`

Expected: PASS.

### Task 3: Route App Entry Points Through The Gateway Session Service

**Files:**
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/http_auth.py`

**Step 1: Write the failing integration-style test**

Add a focused unit or integration test proving that entrypoints no longer create business session ids ad hoc, and instead call the gateway session service.

Suggested assertion:

```python
assert context.gateway_session_service.resolve(...).session_id == exposed_session_id
```

**Step 2: Run targeted tests to confirm failure**

Run: `python -m pytest tests/unit/openclaw/test_gateway_sessions.py tests/integration/test_fastmcp_server.py -q`

Expected: FAIL due to missing app wiring.

**Step 3: Wire app context**

1. construct `GatewaySessionService` in `create_app_context`
2. expose it on `AppContext`
3. update FastMCP session resolution to use it
4. update HTTP auth/session binding to use it before touching session memory

**Step 4: Run targeted tests**

Run: `python -m pytest tests/unit/openclaw/test_gateway_sessions.py tests/integration/test_fastmcp_server.py -q`

Expected: PASS.

### Task 4: Verify No Regressions On Existing Session/Memory Flows

**Files:**
- Test: `tests/e2e/test_http_session_flow.py`
- Test: `tests/integration/test_session_memory_tools.py`

**Step 1: Run session-oriented regressions**

Run: `python -m pytest tests/e2e/test_http_session_flow.py tests/integration/test_session_memory_tools.py -q`

Expected: PASS.

**Step 2: If failures appear, apply the smallest compatibility patch**

Only patch:

1. entrypoint-to-session binding
2. session memory handoff
3. app context initialization

Do not broaden the change into workflow-engine refactors in this phase.

### Task 5: Document The New Boundary

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-04-07-openclaw-agent-migration-design.md`

**Step 1: Update operator-facing docs**

Add a short section documenting:

1. gateway-owned session semantics
2. DM/group/cron session routing
3. this phase as the first OpenClaw-aligned cut

**Step 2: Run final verification**

Run:

```bash
python -m pytest tests/unit/openclaw/test_gateway_sessions.py -q
python -m pytest tests/e2e/test_http_session_flow.py tests/integration/test_session_memory_tools.py -q
python -m pytest tests/integration/test_fastmcp_server.py -q
```

Expected: PASS.
