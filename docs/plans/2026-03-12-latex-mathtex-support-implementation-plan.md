# LaTeX MathTex Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add runtime visibility and preflight failure handling for Manim scripts that use `MathTex`/`Tex`, without making LaTeX a hard requirement for non-math workloads.

**Architecture:** Extend runtime diagnostics so `latex` and `dvisvgm` are reported as optional checks and exposed as a `mathtex` feature capability. Add a small AST-based script inspection step before rendering; if a generated script uses LaTeX-backed Manim objects and the TeX toolchain is unavailable, fail the task with a standardized validation issue before invoking Manim.

**Tech Stack:** Python, Pydantic, pytest, argparse, existing `RuntimeService` / `WorkflowEngine`

---

### Task 1: Runtime diagnostics for MathTex capability

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/doctor/main.py`
- Test: `tests/integration/test_runtime_status_tool.py`
- Test: `tests/integration/test_doctor_cli.py`

**Step 1: Write the failing test**

Add tests that:
- assert runtime status exposes `latex` and `dvisvgm` checks plus a `mathtex` feature summary
- assert `easy-manim-doctor --require-latex` exits successfully only when fake TeX binaries are provided

**Step 2: Run test to verify it fails**

Run: `PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py -q`

Expected: FAIL because runtime diagnostics do not yet expose TeX checks or `--require-latex`.

**Step 3: Write minimal implementation**

Implement:
- `Settings.latex_command` and `Settings.dvisvgm_command`
- env loading for `EASY_MANIM_LATEX_COMMAND` and `EASY_MANIM_DVISVGM_COMMAND`
- runtime checks for those commands
- optional `mathtex` feature summary derived from the TeX checks
- doctor flag `--require-latex` so TeX checks become required only when explicitly requested

**Step 4: Run test to verify it passes**

Run: `PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/config.py src/video_agent/server/main.py src/video_agent/application/runtime_service.py src/video_agent/doctor/main.py tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py
git commit -m "feat: surface mathtex runtime readiness"
```

### Task 2: Preflight failure before render

**Files:**
- Create: `src/video_agent/validation/latex_support.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/validation/test_latex_support.py`
- Test: `tests/integration/test_workflow_completion.py`

**Step 1: Write the failing test**

Add tests that:
- detect `MathTex` / `Tex` usage from generated script text
- assert a task fails with `latex_dependency_missing` when TeX is unavailable but the script uses `MathTex`

**Step 2: Run test to verify it fails**

Run: `PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/unit/validation/test_latex_support.py tests/integration/test_workflow_completion.py -q`

Expected: FAIL because there is no TeX usage detector and no pre-render guard.

**Step 3: Write minimal implementation**

Implement:
- AST-based helpers that detect whether script text references LaTeX-backed Manim calls
- a workflow preflight step after static validation and before render
- standardized validation issue `latex_dependency_missing` with missing command names in details/logging

**Step 4: Run test to verify it passes**

Run: `PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/unit/validation/test_latex_support.py tests/integration/test_workflow_completion.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/validation/latex_support.py src/video_agent/application/workflow_engine.py src/video_agent/server/app.py tests/unit/validation/test_latex_support.py tests/integration/test_workflow_completion.py
git commit -m "feat: fail fast when mathtex dependencies are missing"
```

### Task 3: Docs and real-provider evaluation coverage

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`
- Modify: `docs/runbooks/real-provider-trial.md`
- Modify: `evals/beta_prompt_suite.json`

**Step 1: Write the failing test**

Add or update the smallest existing test that asserts the evaluation suite still parses and the docs mention the new doctor flag only if there is already adjacent coverage. If no useful doc test exists, skip adding doc-only tests.

**Step 2: Run test to verify it fails**

Run the narrowest relevant existing parser/CLI tests if any were updated.

Expected: FAIL only if a real automated assertion was added; otherwise proceed without synthetic doc tests.

**Step 3: Write minimal implementation**

Update docs to:
- mark LaTeX support as optional for general local work
- show that `MathTex`/`Tex` needs `latex` and `dvisvgm`
- recommend `easy-manim-doctor --require-latex` before real math trials

Update the prompt suite with one `real-provider` math-focused case that explicitly asks for `MathTex`.

**Step 4: Run test to verify it passes**

Run any adjacent tests touched in this task.

**Step 5: Commit**

```bash
git add README.md docs/runbooks/local-dev.md docs/runbooks/real-provider-trial.md evals/beta_prompt_suite.json
git commit -m "docs: document mathtex runtime requirements"
```

### Task 4: Final verification

**Files:**
- Verify: `src/video_agent/application/runtime_service.py`
- Verify: `src/video_agent/application/workflow_engine.py`
- Verify: `tests/integration/test_runtime_status_tool.py`
- Verify: `tests/integration/test_doctor_cli.py`
- Verify: `tests/integration/test_workflow_completion.py`
- Verify: `tests/unit/validation/test_latex_support.py`

**Step 1: Run focused verification**

```bash
PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/unit/validation/test_latex_support.py tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py tests/integration/test_workflow_completion.py -q
```

**Step 2: Run full verification**

```bash
PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest -q
```

**Step 3: Review changed files**

```bash
git status -sb
git diff -- src/video_agent/config.py src/video_agent/server/main.py src/video_agent/application/runtime_service.py src/video_agent/doctor/main.py src/video_agent/validation/latex_support.py src/video_agent/application/workflow_engine.py src/video_agent/server/app.py tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py tests/integration/test_workflow_completion.py tests/unit/validation/test_latex_support.py README.md docs/runbooks/local-dev.md docs/runbooks/real-provider-trial.md evals/beta_prompt_suite.json
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add mathtex runtime readiness checks"
```
