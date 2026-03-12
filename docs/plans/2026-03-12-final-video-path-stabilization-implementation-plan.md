# Final Video Path Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure successful renders always produce a stable canonical video artifact at `artifacts/final_video.mp4`, and make task results/resources point to that canonical path instead of Manim's nested output directory.

**Architecture:** Keep Manim rendering into its existing nested media directory, then normalize the produced file into a canonical task artifact path immediately after render. Downstream validation, preview extraction, artifact registration, and MCP resources all operate on the canonical file so helpers and real outputs agree.

**Tech Stack:** Python, pathlib, shutil, pytest, existing `ArtifactStore` / `WorkflowEngine`

---

### Task 1: Reproduce canonical path mismatch

**Files:**
- Modify: `tests/integration/test_workflow_completion.py`
- Modify: `tests/e2e/test_single_task_flow.py`

**Step 1: Write the failing test**

Add assertions that:
- `artifact_store.final_video_path(task_id)` exists after a successful task
- `get_video_result(task_id).video_resource` equals `video-task://<task_id>/artifacts/final_video.mp4`

**Step 2: Run test to verify it fails**

Run: `PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/integration/test_workflow_completion.py tests/e2e/test_single_task_flow.py -q`

Expected: FAIL because renders currently stay in Manim's nested `artifacts/videos/...` tree while the canonical helper path stays empty.

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Run test to verify it still fails**

Repeat the same command and confirm the failure is the expected path mismatch.

**Step 5: Commit**

Do not commit yet.

### Task 2: Normalize final video artifacts

**Files:**
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `tests/integration/test_workflow_completion.py`
- Modify: `tests/e2e/test_single_task_flow.py`

**Step 1: Write the failing test**

Use the tests from Task 1 as the red state.

**Step 2: Run test to verify it fails**

Use the same focused pytest command and inspect the exact failure.

**Step 3: Write minimal implementation**

Implement:
- an `ArtifactStore` helper that promotes a rendered file into `artifacts/final_video.mp4`
- workflow changes so render success normalizes the output before registering the `final_video` artifact
- downstream validation and frame extraction against the canonical file

**Step 4: Run test to verify it passes**

Run: `PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/integration/test_workflow_completion.py tests/e2e/test_single_task_flow.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/storage/artifact_store.py src/video_agent/application/workflow_engine.py tests/integration/test_workflow_completion.py tests/e2e/test_single_task_flow.py
git commit -m "fix: stabilize final video artifact path"
```

### Task 3: Final verification

**Files:**
- Verify: `src/video_agent/adapters/storage/artifact_store.py`
- Verify: `src/video_agent/application/workflow_engine.py`
- Verify: `tests/integration/test_workflow_completion.py`
- Verify: `tests/e2e/test_single_task_flow.py`

**Step 1: Run focused verification**

```bash
PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest tests/integration/test_workflow_completion.py tests/e2e/test_single_task_flow.py tests/integration/test_fastmcp_server.py -q
```

**Step 2: Run full verification**

```bash
PATH=/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH /Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/python -m pytest -q
```

**Step 3: Review diff**

```bash
git diff -- src/video_agent/adapters/storage/artifact_store.py src/video_agent/application/workflow_engine.py tests/integration/test_workflow_completion.py tests/e2e/test_single_task_flow.py
git diff --check
```

**Step 4: Commit**

```bash
git add .
git commit -m "fix: stabilize final video artifact path"
```
