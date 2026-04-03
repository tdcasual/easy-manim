# Memo0 Persistent Memory Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate `memo0` as an optional persistent memory backend that can index promoted memories, power semantic retrieval, and degrade safely to local retrieval when unavailable.

**Architecture:** Keep SQLite `AgentMemoryRecord` as the system of record for ownership, auditability, and fallback retrieval. Add a dedicated `Memo0` backend adapter that syncs local memory records to Mem0 and returns scoped semantic search hits, while `PersistentMemoryService` remains the orchestration layer that merges backend metadata and falls back to local ranking on failure or missing configuration.

**Tech Stack:** Python, Pydantic, FastAPI/MCP existing memory APIs, pytest, optional `mem0ai` SDK

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/unit/application/test_persistent_memory_service.py`
- Modify: `tests/integration/test_agent_memory_tools.py`
- Modify: `tests/unit/test_settings.py`

**Step 1: Add unit coverage for memo0-backed indexing and retrieval**

Write tests that prove:
- promoted session memory stores backend index metadata when memo0 indexing succeeds
- query uses memo0 semantic ordering when backend search succeeds
- query falls back to local retrieval when memo0 backend is unavailable
- disabling a memory propagates delete to the backend when remote IDs exist

**Step 2: Run unit tests to verify they fail**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_persistent_memory_service.py -q`

Expected: FAIL because memo0 backend hooks do not exist yet.

**Step 3: Add integration coverage for tool-level behavior**

Write tests that prove:
- `promote_session_memory` returns indexed memo0 metadata when a fake backend is injected
- `query_agent_memories` returns memo0-ranked results through the MCP tool surface

**Step 4: Run targeted integration tests to verify they fail**

Run:
- `.venv/bin/python -m pytest tests/integration/test_agent_memory_tools.py -q`

Expected: FAIL because app wiring does not provide a memo0 backend yet.

**Step 5: Add config/env coverage**

Write tests that prove:
- settings expose memo0 connection defaults
- `build_settings` reads memo0 env vars

### Task 2: Add Memo0 Backend Adapter

**Files:**
- Create: `src/video_agent/application/memo0_memory_backend.py`
- Modify: `src/video_agent/application/persistent_memory_service.py`
- Modify: `src/video_agent/domain/agent_memory_models.py` only if additional typed payloads are needed

**Step 1: Create a small backend adapter**

Implement a `Memo0MemoryBackend` that:
- lazily imports `mem0`
- initializes `MemoryClient` when configured
- writes promoted records with `client.add(...)`
- searches with `client.search(query, version="v2", filters={"user_id": agent_id}, top_k=limit)`
- deletes remote memories with `client.delete(memory_id=...)`
- returns structured metadata even when unavailable

**Step 2: Extend `PersistentMemoryService` to orchestrate backend usage**

Implement:
- optional backend injection
- backend-aware enhancement payload generation on promote
- backend-first semantic retrieval with local fallback
- backend delete propagation on disable

### Task 3: Wire Config And App Construction

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `pyproject.toml`

**Step 1: Add memo0 config fields**

Add settings/env support for:
- backend selection
- memo0 API key
- org/project IDs

**Step 2: Wire the backend into app creation**

Instantiate the backend once in `create_app_context` and inject it into `PersistentMemoryService`.

**Step 3: Add optional dependency metadata**

Document the expected SDK dependency via `pyproject.toml` without forcing it for the default local backend path.

### Task 4: Verify

**Step 1: Run targeted tests**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_persistent_memory_service.py tests/unit/test_settings.py -q`
- `.venv/bin/python -m pytest tests/integration/test_agent_memory_tools.py -q`

Expected: PASS

**Step 2: Run full suite**

Run:
- `.venv/bin/python -m pytest -q`

Expected: PASS
