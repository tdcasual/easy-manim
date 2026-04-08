# OpenClaw Runtime Bridge Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the remaining runtime-definition compatibility bridge from startup and request paths, then converge HTTP/MCP session handling onto gateway-first control-plane semantics.

**Architecture:** The next phase should stop treating runtime materialization as a normal operating fallback. Runtime definitions must be created on explicit profile/bootstrap paths, while request-time identity resolution only accepts persisted runtime definitions. After that boundary is firm, HTTP and MCP session/auth routing can collapse toward one gateway-owned control-plane flow, and task memory can continue shrinking legacy summary mirrors to read-only compatibility fields.

**Tech Stack:** Python 3.13, FastAPI, FastMCP, Pydantic, SQLite, pytest, OpenClaw-style gateway session layer

---

### Task 1: Freeze The Runtime-Definition-Only Boundary In Tests

**Files:**
- Modify: `tests/unit/application/test_agent_runtime_service.py`
- Modify: `tests/unit/application/test_agent_identity_service.py`
- Modify: `tests/integration/test_http_auth_api.py`
- Modify: `tests/integration/test_agent_auth_tools.py`

**Step 1: Write the failing tests**

Add tests that prove:

1. `AgentRuntimeDefinitionService.resolve(...)` is no longer allowed to synthesize a default materialized definition on demand.
2. `AgentIdentityService.resolve_principal(...)` fails when a profile/token pair exists but no persisted runtime definition exists.
3. HTTP session login fails clearly when a runtime definition has not been provisioned.
4. MCP authentication fails clearly when a runtime definition has not been provisioned.

Suggested assertions:

```python
with pytest.raises(ValueError, match="agent runtime definition not found"):
    service.resolve("agent-a", profile=profile)
```

```python
response = client.post("/api/sessions", json={"agent_token": plain_token})
assert response.status_code == 401
assert response.json()["detail"] == "invalid_agent_token"
```

**Step 2: Run targeted tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/application/test_agent_runtime_service.py \
  tests/unit/application/test_agent_identity_service.py \
  tests/integration/test_http_auth_api.py \
  tests/integration/test_agent_auth_tools.py \
  -q
```

Expected: FAIL because runtime resolution still has a request-time materialization path and startup backfill still hides missing definitions.

**Step 3: Tighten test language**

Keep the failure contract narrow:

1. missing runtime definition stays a `ValueError("agent runtime definition not found")`
2. request surfaces translate that to existing auth failures
3. explicit runtime definitions remain the only accepted source of truth

**Step 4: Re-run the same tests**

Run the same command again and confirm only the intended failures remain.

### Task 2: Remove Startup-Time Runtime Materialization As A Normal Path

**Files:**
- Modify: `src/video_agent/application/agent_runtime_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/application/agent_identity_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_agent_profile_store.py`
- Test: `tests/unit/application/test_agent_runtime_service.py`
- Test: `tests/unit/application/test_agent_identity_service.py`

**Step 1: Remove request-time synthesis**

Change `AgentRuntimeDefinitionService` so that:

1. `resolve(...)` delegates to `require_persisted(...)`
2. `build_default_definition(...)` remains available only for explicit provisioning flows
3. `ensure_persisted(...)` is retained only where creation/backfill is still intentionally invoked

**Step 2: Remove app-start backfill**

Delete the `create_app_context(...)` call to:

```python
agent_runtime_definition_service.ensure_persisted_for_profiles(
    store.list_agent_profiles(status="active"),
)
```

The app should now assume runtime definitions already exist.

**Step 3: Keep explicit creation paths authoritative**

Ensure `SQLiteAgentProfileStoreMixin.upsert_agent_profile(...)` remains the primary provisioning point for default materialized runtime definitions, including the current sync-on-update behavior for materialized definitions.

**Step 4: Run targeted tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/application/test_agent_runtime_service.py \
  tests/unit/application/test_agent_identity_service.py \
  tests/integration/test_http_auth_api.py \
  tests/integration/test_agent_auth_tools.py \
  -q
```

Expected: PASS.

### Task 3: Verify Bootstrap And Admin Flows Still Provision Runtime Definitions

**Files:**
- Modify: `tests/integration/test_agent_admin_cli.py`
- Modify: `tests/unit/adapters/storage/test_sqlite_agent_runtime_store.py`
- Modify: `tests/unit/application/test_agent_session_service.py`

**Step 1: Write coverage for explicit provisioning paths**

Add tests that prove:

1. admin/bootstrap flows still create a persisted runtime definition when they create a profile
2. profile updates continue syncing materialized runtime definitions without mutating explicit definitions
3. session creation continues to work when the runtime definition exists

Suggested assertions:

```python
runtime = store.get_agent_runtime_definition(agent_id)
assert runtime is not None
assert runtime.definition_source == "materialized"
```

**Step 2: Run targeted provisioning regressions**

Run:

```bash
.venv/bin/python -m pytest \
  tests/integration/test_agent_admin_cli.py \
  tests/unit/adapters/storage/test_sqlite_agent_runtime_store.py \
  tests/unit/application/test_agent_session_service.py \
  -q
```

Expected: PASS.

**Step 3: If failures appear, patch only provisioning boundaries**

Allowed fixes:

1. profile upsert provisioning
2. profile-update synchronization for materialized definitions
3. CLI/bootstrap setup code

Do not reintroduce startup backfill.

### Task 4: Collapse HTTP Session Resolution Toward Gateway-First Control Plane

**Files:**
- Modify: `src/video_agent/server/http_auth.py`
- Modify: `src/video_agent/server/http_api_identity_routes.py`
- Modify: `src/video_agent/server/http_api_task_routes.py`
- Modify: `src/video_agent/server/http_api_profile_memory_routes.py`
- Modify: `src/video_agent/server/http_api_video_thread_routes.py`
- Test: `tests/e2e/test_http_session_flow.py`
- Test: `tests/integration/test_http_auth_api.py`
- Test: `tests/integration/test_http_task_api.py`

**Step 1: Write a failing HTTP contract test**

Add coverage that proves HTTP request handling always uses the gateway-owned session id exposed by `resolve_agent_session(...)`, and that task/profile memory routes no longer reconstruct transport-shaped session state ad hoc.

Suggested assertion:

```python
assert payload["session_id"] == expected_gateway_session_id
```

Or, if session ids are intentionally stripped from the HTTP payload, assert through stored runtime runs or session memory snapshots instead.

**Step 2: Refactor `ResolvedAgentSession` into the HTTP control-plane boundary**

Consolidate:

1. agent principal
2. gateway session id
3. raw session token only where revocation still needs it

Then make HTTP routes consume that object directly instead of manually re-deriving request session context.

**Step 3: Record runtime auth/run activity off the gateway session**

Audit login and task entrypoints so `AgentRuntimeRunService` always records against the gateway session id, not the legacy `AgentSession.session_id`.

**Step 4: Run targeted HTTP regressions**

Run:

```bash
.venv/bin/python -m pytest \
  tests/e2e/test_http_session_flow.py \
  tests/integration/test_http_auth_api.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  -q
```

Expected: PASS.

### Task 5: Replace MCP Transport Session Assembly With Gateway Session Binding

**Files:**
- Modify: `src/video_agent/server/session_auth.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_tools_auth.py`
- Modify: `src/video_agent/server/fastmcp_server_memory_registration.py`
- Modify: `src/video_agent/server/fastmcp_server_task_registration.py`
- Test: `tests/integration/test_fastmcp_server.py`
- Test: `tests/integration/test_mcp_tools.py`
- Test: `tests/integration/test_mcp_multi_agent_workflow_tools.py`

**Step 1: Write failing MCP tests around session ownership**

Add coverage that proves:

1. transport context only contributes route hints
2. gateway session service owns the final session id
3. authenticated MCP calls share the same gateway session for the same route

Suggested assertion:

```python
assert first_session_id == second_session_id
assert runtime_run.session_id == first_session_id
```

**Step 2: Introduce a gateway-oriented MCP session resolver**

Refactor `session_key_for_context(...)` usage so it is no longer treated as the session id itself. It should become a transport route key or disappear behind a single resolver function in `fastmcp_server.py`.

**Step 3: Minimize `SessionAuthRegistry` scope**

Keep it only as an authentication binding cache if still needed, but remove any implication that it owns the business session id.

**Step 4: Run targeted MCP regressions**

Run:

```bash
.venv/bin/python -m pytest \
  tests/integration/test_fastmcp_server.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_agent_auth_tools.py \
  -q
```

Expected: PASS.

### Task 6: Shrink Legacy Task Memory Fields To Compatibility Mirrors

**Files:**
- Modify: `src/video_agent/application/task_memory_context.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/server/http_api_task_routes.py`
- Test: `tests/unit/application/test_task_memory_context.py`
- Test: `tests/unit/application/test_workflow_collaboration_memory.py`
- Test: `tests/integration/test_review_bundle_builder.py`
- Test: `tests/integration/test_http_task_api.py`

**Step 1: Write failing tests for structured-first outputs**

Add tests that prove:

1. HTTP task payloads and review bundles expose `task_memory_context` as the authoritative memory structure
2. workflow review state reads pinned memory ids and summaries from `task_memory_context["persistent"]`
3. legacy summary fields still mirror data when present, but new reads do not depend on them

**Step 2: Reduce legacy write-model pressure**

Update workflow/memory assembly paths so:

1. structured `task_memory_context` is written first
2. legacy fields are populated only as mirrors for compatibility
3. new readers no longer require `selected_memory_ids` or summary digest columns to reconstruct state

**Step 3: Run targeted memory regressions**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/application/test_task_memory_context.py \
  tests/unit/application/test_workflow_collaboration_memory.py \
  tests/integration/test_review_bundle_builder.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_eval_strategy_promotion.py \
  -q
```

Expected: PASS.

### Task 7: Run The Full OpenClaw Migration Regression Slice

**Files:**
- Test: `tests/unit/openclaw/test_gateway_sessions.py`
- Test: `tests/unit/server/test_session_memory.py`
- Test: `tests/unit/application/test_agent_runtime_service.py`
- Test: `tests/unit/application/test_agent_identity_service.py`
- Test: `tests/unit/application/test_agent_session_service.py`
- Test: `tests/unit/server/test_mcp_tool_helpers.py`
- Test: `tests/unit/adapters/storage/test_sqlite_agent_runtime_store.py`
- Test: `tests/unit/adapters/storage/test_sqlite_agent_runtime_run_store.py`
- Test: `tests/unit/application/test_session_memory_service.py`
- Test: `tests/unit/application/test_persistent_memory_service.py`
- Test: `tests/unit/application/test_task_memory_context.py`
- Test: `tests/unit/application/test_auto_repair_service.py`
- Test: `tests/unit/application/test_task_service_child_tasks.py`
- Test: `tests/unit/application/test_repair_prompt_builder.py`
- Test: `tests/unit/application/test_workflow_collaboration_memory.py`
- Test: `tests/unit/application/test_workflow_collaboration_service.py`
- Test: `tests/unit/application/test_task_service_projection.py`
- Test: `tests/unit/adapters/llm/test_prompt_builder.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`
- Test: `tests/integration/test_agent_admin_cli.py`
- Test: `tests/integration/test_agent_auth_tools.py`
- Test: `tests/integration/test_agent_runtime_runs.py`
- Test: `tests/integration/test_agent_memory_tools.py`
- Test: `tests/integration/test_fastmcp_server.py`
- Test: `tests/e2e/test_http_session_flow.py`
- Test: `tests/integration/test_http_auth_api.py`
- Test: `tests/integration/test_revision_and_cancel.py`
- Test: `tests/integration/test_workflow_completion.py`
- Test: `tests/integration/test_mcp_tools.py`
- Test: `tests/integration/test_auto_repair_loop.py`
- Test: `tests/integration/test_http_task_api.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Test: `tests/integration/test_task_service_create_get.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Test: `tests/integration/test_eval_strategy_promotion.py`
- Test: `tests/integration/test_review_bundle_builder.py`

**Step 1: Run the full regression slice**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/openclaw/test_gateway_sessions.py \
  tests/unit/server/test_session_memory.py \
  tests/unit/application/test_agent_runtime_service.py \
  tests/unit/application/test_agent_identity_service.py \
  tests/unit/application/test_agent_session_service.py \
  tests/unit/server/test_mcp_tool_helpers.py \
  tests/unit/adapters/storage/test_sqlite_agent_runtime_store.py \
  tests/unit/adapters/storage/test_sqlite_agent_runtime_run_store.py \
  tests/unit/application/test_session_memory_service.py \
  tests/unit/application/test_persistent_memory_service.py \
  tests/unit/application/test_task_memory_context.py \
  tests/unit/application/test_auto_repair_service.py \
  tests/unit/application/test_task_service_child_tasks.py \
  tests/unit/application/test_repair_prompt_builder.py \
  tests/unit/application/test_workflow_collaboration_memory.py \
  tests/unit/application/test_workflow_collaboration_service.py \
  tests/unit/application/test_task_service_projection.py \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_agent_admin_cli.py \
  tests/integration/test_agent_auth_tools.py \
  tests/integration/test_agent_runtime_runs.py \
  tests/integration/test_agent_memory_tools.py \
  tests/integration/test_fastmcp_server.py \
  tests/e2e/test_http_session_flow.py \
  tests/integration/test_http_auth_api.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_eval_run_cli.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_review_bundle_builder.py \
  -q
```

Expected: PASS.

**Step 2: If regressions appear, constrain fixes to this migration slice**

Allowed fix areas:

1. runtime-definition provisioning/resolution
2. gateway session routing and auth binding
3. structured task memory projection

Do not expand into unrelated frontend or product-surface refactors.

### Task 8: Document The New Post-Bridge Architecture

**Files:**
- Modify: `docs/plans/2026-04-07-openclaw-agent-migration-design.md`
- Modify: `README.md`
- Create or Modify: `docs/plans/2026-04-08-openclaw-runtime-bridge-removal-plan.md`

**Step 1: Update migration status**

Document:

1. startup backfill removed
2. persisted runtime definitions are mandatory
3. HTTP/MCP route only through gateway-owned session ids
4. `task_memory_context` is the structured memory read model

**Step 2: Record remaining cleanup after this phase**

Track only the next tail items:

1. remove obsolete `AgentSessionService` centrality where only control-plane auth metadata remains
2. collapse transport-specific auth caches further if they become redundant
3. consider dropping legacy task memory mirror fields after external consumers migrate

**Step 3: Final documentation sanity check**

Read:

```bash
sed -n '1,260p' docs/plans/2026-04-07-openclaw-agent-migration-design.md
sed -n '1,260p' docs/plans/2026-04-08-openclaw-runtime-bridge-removal-plan.md
```

Expected: docs match the implemented boundary and do not describe startup/request-time runtime materialization as a supported path.
