# Project Hygiene And Quality Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve repository hygiene, add backend quality gates, and complete a low-risk first split of the HTTP API support layer.

**Architecture:** Keep behavior stable while extracting support code out of the HTTP API module, tightening import-time safety for CLI and smoke helpers, and removing generated artifacts from version control. Favor small refactors with characterization tests over broad rewrites.

**Tech Stack:** Python, FastAPI, pytest, GitHub Actions, Ruff

---

### Task 1: Lock import-safety and HTTP helper behavior with tests

**Files:**
- Create: `tests/unit/server/test_http_api_support.py`
- Create: `tests/integration/test_import_safety.py`
- Verify: `tests/integration/test_http_api.py`

**Step 1: Write the failing tests**

- Add unit tests for task artifact URI normalization, download URL derivation, and session-field stripping.
- Add import-safety tests that prove:
  - `video_agent.server.api_main` can be imported even if `uvicorn` is unavailable.
  - `scripts.beta_smoke` can be imported even if `mcp` is unavailable.

**Step 2: Run tests to verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/server/test_http_api_support.py tests/integration/test_import_safety.py -q
```

Expected: failures because the support module does not exist yet and imports are still eager.

### Task 2: Split HTTP API support code

**Files:**
- Create: `src/video_agent/server/http_api_support.py`
- Modify: `src/video_agent/server/http_api.py`

**Step 1: Write minimal implementation**

- Move request payload models and small helper functions out of `http_api.py`.
- Keep route behavior identical.
- Reduce top-of-file clutter in `http_api.py`.

**Step 2: Run focused tests**

Run:

```bash
.venv/bin/pytest tests/unit/server/test_http_api_support.py tests/integration/test_http_api.py -q
```

Expected: all passing.

### Task 3: Add backend quality gates

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `src/video_agent/server/api_main.py`
- Modify: `scripts/beta_smoke.py`

**Step 1: Tighten runtime import boundaries**

- Lazy-import `uvicorn` inside `main`.
- Lazy-import MCP client dependencies inside smoke-runtime functions only.

**Step 2: Add lint gate**

- Add `ruff` to dev dependencies and minimal config.
- Run Ruff in CI before tests.

**Step 3: Run focused verification**

Run:

```bash
.venv/bin/pytest tests/integration/test_import_safety.py tests/integration/test_cli_entrypoints.py tests/e2e/test_release_candidate_gate.py -q
```

Expected: import-safety tests pass and existing entrypoint tests stay green.

### Task 4: Clean generated artifacts out of the repo

**Files:**
- Modify: `.gitignore`
- Remove: `ui/coverage/**`
- Remove: `ui/src/app/*.bak`

**Step 1: Strengthen ignore rules**

- Add root-level ignores for UI-generated artifacts and backup files.

**Step 2: Remove tracked generated files**

- Delete committed coverage output and backup files.

**Step 3: Verify repository state**

Run:

```bash
git status --short
git ls-files | rg '(^|/)(coverage|dist|node_modules)/|\.bak$'
```

Expected: no tracked UI coverage files or `.bak` files remain.

### Task 5: Final verification

**Files:**
- Verify only

**Step 1: Run final focused checks**

```bash
.venv/bin/pytest tests/unit/server/test_http_api_support.py tests/integration/test_import_safety.py tests/integration/test_http_api.py tests/integration/test_cli_entrypoints.py tests/e2e/test_release_candidate_gate.py -q
.venv/bin/python -m ruff check src tests scripts
```

**Step 2: Summarize residual risk**

- Note that this is the first slice of large-file splitting, not the full decomposition of all oversized modules.
