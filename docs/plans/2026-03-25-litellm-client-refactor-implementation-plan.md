# LiteLLM Client Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current OpenAI-compatible model client path with a LiteLLM-backed client, update configuration/env handling and docs, and keep the project runnable end-to-end with focused test coverage.

**Architecture:** Keep the existing `LLMClient` protocol and `StubLLMClient` path, but replace the real-provider adapter with a new `LiteLLMClient` that delegates completion calls to LiteLLM and normalizes provider failures into the existing workflow error types. Update settings/env parsing so the only real-provider mode is `litellm`, rename provider config from `llm_base_url` to `llm_api_base`, and update runtime diagnostics/docs/tests to match the new contract.

**Tech Stack:** Python 3.10+, Pydantic v2, FastAPI app wiring, LiteLLM, pytest, existing runtime/doctor CLI.

---

### Task 1: Replace the provider adapter surface

**Files:**
- Create: `src/video_agent/adapters/llm/litellm_client.py`
- Modify: `src/video_agent/adapters/llm/client.py`
- Modify: `src/video_agent/adapters/llm/__init__.py`
- Delete: `src/video_agent/adapters/llm/openai_compatible_client.py`
- Delete: `tests/unit/adapters/llm/test_openai_compatible_client.py`
- Test: `tests/unit/adapters/llm/test_litellm_client.py`

**Step 1: Write the failing adapter tests**

Create `tests/unit/adapters/llm/test_litellm_client.py` with focused cases for:

```python
def test_litellm_client_calls_completion_with_expected_kwargs() -> None: ...
def test_litellm_client_maps_auth_errors() -> None: ...
def test_litellm_client_sanitizes_fenced_code() -> None: ...
```

The tests should inject a fake LiteLLM module object so they do not depend on a real network call or an installed provider SDK.

**Step 2: Run the adapter tests to verify they fail**

Run: `python3 -m pytest tests/unit/adapters/llm/test_litellm_client.py -q`

Expected: FAIL because `LiteLLMClient` and the new imports do not exist yet.

**Step 3: Implement the LiteLLM adapter**

Implement `LiteLLMClient` in `src/video_agent/adapters/llm/litellm_client.py`:

```python
class LiteLLMClient:
    def __init__(..., model: str, api_base: str | None = None, api_key: str | None = None, ...):
        ...

    def generate_script(self, prompt_text: str) -> str:
        response = self._completion(...)
        content = sanitize_script_text(self._extract_content(response))
        ...
```

Move shared provider exception types into `src/video_agent/adapters/llm/client.py` so workflow code no longer depends on a provider-specific module path.

**Step 4: Run the adapter tests to verify they pass**

Run: `python3 -m pytest tests/unit/adapters/llm/test_litellm_client.py -q`

Expected: PASS

### Task 2: Replace config and app wiring

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/unit/test_settings.py`
- Test: `tests/integration/test_runtime_status_tool.py`
- Test: `tests/integration/test_generation_provider_failures.py`
- Test: `tests/integration/test_auto_repair_loop.py`

**Step 1: Write the failing config/runtime tests**

Extend tests to assert the new contract:

```python
def test_build_settings_reads_litellm_env(monkeypatch) -> None:
    monkeypatch.setenv("EASY_MANIM_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("EASY_MANIM_LLM_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("EASY_MANIM_LLM_API_BASE", "https://example.test/v1")
    ...

def test_runtime_status_tool_reports_api_base_presence(tmp_path) -> None:
    assert payload["provider"]["mode"] == "stub"
    assert payload["provider"]["api_base_present"] is False
```

Update provider-failure tests to use `llm_provider="litellm"` and `llm_api_base`.

**Step 2: Run the focused config/runtime tests to verify they fail**

Run:
- `python3 -m pytest tests/unit/test_settings.py -q`
- `python3 -m pytest tests/integration/test_runtime_status_tool.py tests/integration/test_generation_provider_failures.py tests/integration/test_auto_repair_loop.py -q`

Expected: FAIL because the settings fields and provider names still use the old OpenAI-compatible shape.

**Step 3: Implement the config and wiring refactor**

Update:
- `Settings` to use `llm_provider` values `stub|litellm`
- `llm_api_base` instead of `llm_base_url`
- `build_settings()` to read `EASY_MANIM_LLM_API_BASE`
- `_build_llm_client()` to build `LiteLLMClient`
- runtime diagnostics to expose `api_base_present`
- workflow imports to use provider errors from the shared adapter module

`_build_llm_client()` should reject `litellm` mode when `llm_model` still points at the stub default.

**Step 4: Run the focused config/runtime tests to verify they pass**

Run:
- `python3 -m pytest tests/unit/test_settings.py -q`
- `python3 -m pytest tests/integration/test_runtime_status_tool.py tests/integration/test_generation_provider_failures.py tests/integration/test_auto_repair_loop.py -q`

Expected: PASS

### Task 3: Update dependency metadata and operator docs

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `.env.beta.example`
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`
- Modify: `docs/runbooks/real-provider-trial.md`
- Modify: `docs/runbooks/agent-self-serve.md`
- Modify: `docs/runbooks/beta-ops.md`
- Modify: `docs/runbooks/http-api-deploy.md`

**Step 1: Write the failing expectations into docs/config examples**

Replace references to:
- `openai_compatible` -> `litellm`
- `EASY_MANIM_LLM_BASE_URL` -> `EASY_MANIM_LLM_API_BASE`
- raw OpenAI-specific wording -> LiteLLM model-routing wording

Add `litellm` to `pyproject.toml` dependencies.

**Step 2: Run a repo-wide search to verify stale references remain before the edit**

Run: `rg -n "openai_compatible|EASY_MANIM_LLM_BASE_URL|OpenAICompatibleLLMClient" .`

Expected: matches across source, tests, and docs.

**Step 3: Update docs and dependency declarations**

Make the public docs consistently describe:
- `stub` for deterministic local/test mode
- `litellm` for any real provider path
- `EASY_MANIM_LLM_MODEL` as the main routing knob
- `EASY_MANIM_LLM_API_BASE` / `EASY_MANIM_LLM_API_KEY` as optional provider-specific overrides

**Step 4: Run the stale-reference search again**

Run: `rg -n "openai_compatible|EASY_MANIM_LLM_BASE_URL|OpenAICompatibleLLMClient" src tests docs README.md .env.example .env.beta.example pyproject.toml`

Expected: no matches

### Task 4: End-to-end focused verification

**Files:**
- Verify only; no new files required unless a test fix is needed

**Step 1: Run the focused migration slice**

Run:
- `python3 -m pytest tests/unit/adapters/llm/test_litellm_client.py -q`
- `python3 -m pytest tests/unit/test_settings.py -q`
- `python3 -m pytest tests/integration/test_runtime_status_tool.py tests/integration/test_generation_provider_failures.py tests/integration/test_auto_repair_loop.py -q`

Expected: PASS

**Step 2: Run a broader smoke slice around workflow/import safety**

Run:
- `python3 -m pytest tests/unit/test_import_smoke.py tests/unit/adapters/llm/test_stub_client.py tests/integration/test_cli_entrypoints.py -q`

Expected: PASS

**Step 3: Review git diff for accidental compatibility leftovers**

Run:
- `git diff -- src/video_agent/adapters/llm src/video_agent/server src/video_agent/application/runtime_service.py src/video_agent/config.py tests docs README.md pyproject.toml`

Expected: only LiteLLM-oriented refactor changes, no unrelated edits.
