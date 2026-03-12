# MCP Validated Video Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在单机 Python 环境下交付一个可运行的 MCP 视频 Agent：支持异步创建任务、后台生成与渲染 Manim、结构化验证结果、查询 artifacts，并支持基于已有结果继续 revision。

**Architecture:** 保持单语言、单机、单 worker 的实现路径。`server` 只暴露 MCP tools/resources，`application` 负责编排任务状态流，`adapters` 负责 SQLite、文件系统、LLM、Manim、ffmpeg 等外部交互，`validation` 负责静态检查、硬校验和规则校验；所有长任务都通过 SQLite lease + 本地 worker 异步推进。

**Tech Stack:** Python 3.11+, MCP Python SDK, Pydantic, SQLite, pytest, ffmpeg/ffprobe, OpenCV, Manim Community, Rich

---

## 推荐节奏

推荐采用 **6 周单人节奏**，而不是 3 周压缩版：
1. 当前仓库几乎为空，需要先补基础设施。
2. 项目风险不在“写出 MCP 接口”，而在“把渲染、验证、状态机串起来并能回放问题”。
3. 每周预留 1 天做稳定化、修文档、补测试，避免把所有风险堆到最后一周。

每周都遵守同一退出标准：
1. 本周新增测试全部通过。
2. 至少有 1 条可复现的 happy path 或 failure path。
3. 本周新增文件路径与职责边界不反复推翻。
4. `README.md` 或 `docs/runbooks` 补齐最低限度运行说明。

## 全局实现假设

1. v1 只支持 **单个配置好的 LLM provider**，不做多 provider 竞赛。
2. v1 只要求 **单 worker 进程**，通过 SQLite lease 防止重复消费。
3. v1 的第一个可运行版本只要求 **单 scene happy path**。
4. `subprocess` 禁止的是 **LLM 生成脚本内部调用**，不是宿主系统调用 Manim/ffmpeg。
5. 所有 artifacts 存本地文件系统，结构化索引存 SQLite。
6. 先用轮询式 worker，不引入 Redis、Celery、Postgres、S3。

## 目录冻结

第一周内创建并冻结如下目录，后续只增量扩展，不大改：

```text
src/
  video_agent/
    server/
    application/
    domain/
    adapters/
      llm/
      rendering/
      storage/
    validation/
    worker/
    observability/
    safety/
tests/
  unit/
  integration/
  e2e/
docs/
  plans/
  runbooks/
data/
```

---

## Week 1 - 项目脚手架与核心模型

**目标：** 建立 Python 包、测试骨架、核心领域模型，保证后续所有任务都能围绕稳定 schema 实现。

**本周退出标准：**
1. `pytest` 能跑通基础单测。
2. `VideoTask`、状态枚举、验证报告 schema 已冻结为第一版。
3. 开发者可以本地创建 SQLite 文件并加载配置。

### Task 1: Scaffold package and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/video_agent/__init__.py`
- Create: `src/video_agent/config.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_import_smoke.py`

**Step 1: Write the failing test**

```python
from video_agent.config import Settings


def test_settings_has_default_data_dir() -> None:
    settings = Settings()
    assert str(settings.data_dir).endswith("data")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_import_smoke.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_agent'`

**Step 3: Write minimal implementation**

```python
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    data_dir: Path = Path("data")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_import_smoke.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/video_agent/__init__.py src/video_agent/config.py tests/conftest.py tests/unit/test_import_smoke.py
git commit -m "chore: bootstrap python package and tests"
```

### Task 2: Define enums and domain models

**Files:**
- Create: `src/video_agent/domain/enums.py`
- Create: `src/video_agent/domain/models.py`
- Create: `src/video_agent/domain/validation_models.py`
- Create: `tests/unit/domain/test_models.py`

**Step 1: Write the failing tests**

```python
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


def test_video_task_defaults() -> None:
    task = VideoTask(prompt="draw a circle")
    assert task.status is TaskStatus.QUEUED
    assert task.phase is TaskPhase.QUEUED
    assert task.attempt_count == 0
    assert task.root_task_id == task.task_id


def test_child_task_keeps_root_and_parent() -> None:
    parent = VideoTask(prompt="draw a circle")
    child = VideoTask.from_revision(parent=parent, feedback="make it blue")
    assert child.parent_task_id == parent.task_id
    assert child.root_task_id == parent.root_task_id
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/domain/test_models.py -q`
Expected: FAIL with import or attribute errors

**Step 3: Write minimal implementation**

Implement:
- `TaskStatus`: `queued`, `running`, `revising`, `completed`, `failed`, `cancelled`
- `TaskPhase`: `queued`, `planning`, `generating_code`, `static_check`, `rendering`, `frame_extract`, `validation`, `revising`, `completed`, `failed`, `cancelled`
- `VideoTask` Pydantic model with `task_id`, `root_task_id`, `parent_task_id`, `prompt`, `feedback`, `output_profile`, `validation_profile`, `attempt_count`, `created_at`, `updated_at`
- `VideoTask.from_revision(...)`
- `ValidationReport`, `ValidationIssue`, `ValidationDecision`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/domain/test_models.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/domain/enums.py src/video_agent/domain/models.py src/video_agent/domain/validation_models.py tests/unit/domain/test_models.py
git commit -m "feat: define task and validation domain models"
```

### Task 3: Add configuration and local runbook

**Files:**
- Modify: `src/video_agent/config.py`
- Create: `docs/runbooks/local-dev.md`
- Create: `.env.example`
- Create: `tests/unit/test_settings.py`

**Step 1: Write the failing test**

```python
from video_agent.config import Settings


def test_settings_exposes_database_and_artifact_dirs() -> None:
    settings = Settings()
    assert settings.database_path.name == "video_agent.db"
    assert settings.artifact_root.name == "tasks"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_settings.py -q`
Expected: FAIL because fields are missing

**Step 3: Write minimal implementation**

Add to `Settings`:
- `database_path = Path("data/video_agent.db")`
- `artifact_root = Path("data/tasks")`
- `manim_command = "manim"`
- `ffmpeg_command = "ffmpeg"`
- `ffprobe_command = "ffprobe"`
- `default_poll_after_ms = 2000`

Document in `docs/runbooks/local-dev.md`:
- Python version
- Manim/ffmpeg prerequisites
- How to run tests
- Where artifacts are written

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_settings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/config.py docs/runbooks/local-dev.md .env.example tests/unit/test_settings.py
git commit -m "docs: add local environment configuration"
```

---

## Week 2 - 存储层、任务服务、基础 MCP 接口

**目标：** 让系统真正能“创建任务、持久化任务、查询任务”，哪怕 worker 还没跑完整工作流。

**本周退出标准：**
1. 可以调用服务层创建 `VideoTask` 并落到 SQLite。
2. 可以通过 MCP tools 读取任务快照。
3. 幂等键 `idempotency_key` 生效。

### Task 4: Implement SQLite store and schema bootstrap

**Files:**
- Create: `src/video_agent/adapters/storage/schema.sql`
- Create: `src/video_agent/adapters/storage/sqlite_store.py`
- Create: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing tests**

```python
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.models import VideoTask


def test_store_can_insert_and_fetch_task(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(prompt="draw a circle")
    store.create_task(task, idempotency_key="abc")

    loaded = store.get_task(task.task_id)
    assert loaded is not None
    assert loaded.prompt == "draw a circle"


def test_idempotency_key_returns_existing_task(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    first = VideoTask(prompt="draw a circle")
    second = VideoTask(prompt="draw another circle")

    created = store.create_task(first, idempotency_key="same")
    duplicate = store.create_task(second, idempotency_key="same")
    assert duplicate.task_id == created.task_id
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/adapters/storage/test_sqlite_store.py -q`
Expected: FAIL with missing store implementation

**Step 3: Write minimal implementation**

Implement:
- `video_tasks` table
- `task_events` table
- `task_artifacts` table
- `task_validations` table
- `task_leases` table
- `idempotency_key` unique index on `video_tasks`
- `SQLiteTaskStore.initialize()`
- `create_task()`, `get_task()`, `append_event()`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/adapters/storage/test_sqlite_store.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/storage/schema.sql src/video_agent/adapters/storage/sqlite_store.py tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: add sqlite task store"
```

### Task 5: Implement artifact store and task service

**Files:**
- Create: `src/video_agent/adapters/storage/artifact_store.py`
- Create: `src/video_agent/application/task_service.py`
- Create: `tests/integration/test_task_service_create_get.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.application.task_service import TaskService


def test_create_task_returns_poll_metadata(task_service: TaskService) -> None:
    result = task_service.create_video_task(prompt="draw a circle", idempotency_key="k1")
    assert result.task_id
    assert result.status == "queued"
    assert result.poll_after_ms == 2000


def test_get_task_returns_snapshot(task_service: TaskService) -> None:
    created = task_service.create_video_task(prompt="draw a circle", idempotency_key="k2")
    snapshot = task_service.get_video_task(created.task_id)
    assert snapshot.task_id == created.task_id
    assert snapshot.phase == "queued"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_task_service_create_get.py -q`
Expected: FAIL with missing service

**Step 3: Write minimal implementation**

Implement:
- `ArtifactStore.ensure_task_dirs(task_id)`
- `TaskService.create_video_task(...)`
- `TaskService.get_video_task(task_id)`
- response DTOs for create/get/result summary
- automatic `task.json` materialization into task directory

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_task_service_create_get.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/storage/artifact_store.py src/video_agent/application/task_service.py tests/integration/test_task_service_create_get.py
git commit -m "feat: add task service create and get"
```

### Task 6: Expose minimal MCP tools/resources

**Files:**
- Create: `src/video_agent/server/mcp_tools.py`
- Create: `src/video_agent/server/mcp_resources.py`
- Create: `src/video_agent/server/app.py`
- Create: `tests/integration/test_mcp_tools.py`

**Step 1: Write the failing tests**

```python
from video_agent.server.mcp_tools import create_video_task_tool, get_video_task_tool


def test_create_video_task_tool_returns_task_id(app_context) -> None:
    payload = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    assert payload["task_id"]
    assert payload["status"] == "queued"


def test_get_video_task_tool_returns_snapshot(app_context) -> None:
    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    snapshot = get_video_task_tool(app_context, {"task_id": created["task_id"]})
    assert snapshot["task_id"] == created["task_id"]
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_mcp_tools.py -q`
Expected: FAIL with missing tool functions

**Step 3: Write minimal implementation**

Implement:
- `create_video_task`
- `get_video_task`
- `get_video_result` (returns not-ready response for non-completed tasks)
- MCP resource handlers for `task.json`
- app factory that wires settings, stores, services

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_mcp_tools.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/mcp_tools.py src/video_agent/server/mcp_resources.py src/video_agent/server/app.py tests/integration/test_mcp_tools.py
git commit -m "feat: expose basic mcp task tools"
```

---

## Week 3 - Worker、生成、静态检查、渲染 happy path

**目标：** 打通一条真正的异步流水线：worker 拿到 queued 任务，生成脚本，静态检查，通过后渲染并写回结果。

**本周退出标准：**
1. 单 worker 可用 lease 抢占 queued 任务。
2. 至少有 1 条 happy path 能走到 `rendering` 结束。
3. 对明显危险脚本能在 `static_check` 阶段失败。

### Task 7: Implement worker loop and lease-based execution

**Files:**
- Create: `src/video_agent/application/workflow_engine.py`
- Create: `src/video_agent/worker/worker_loop.py`
- Create: `tests/integration/test_worker_leases.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.worker.worker_loop import WorkerLoop


def test_worker_claims_queued_task_once(app_context) -> None:
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="lease")
    worker = WorkerLoop(app_context)
    processed = worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert processed == 1
    assert snapshot.phase != "queued"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_worker_leases.py -q`
Expected: FAIL with missing worker or lease logic

**Step 3: Write minimal implementation**

Implement:
- `SQLiteTaskStore.claim_next_task(worker_id, lease_seconds)`
- `SQLiteTaskStore.release_lease(task_id, worker_id)`
- `WorkflowEngine.run_task(task_id)`
- `WorkerLoop.run_once()`
- phase transition event logging

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_worker_leases.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/workflow_engine.py src/video_agent/worker/worker_loop.py tests/integration/test_worker_leases.py
git commit -m "feat: add worker loop with sqlite lease"
```

### Task 8: Implement prompt normalization, LLM adapter, and static check

**Files:**
- Create: `src/video_agent/adapters/llm/client.py`
- Create: `src/video_agent/adapters/llm/prompt_builder.py`
- Create: `src/video_agent/validation/static_check.py`
- Create: `tests/unit/adapters/llm/test_prompt_builder.py`
- Create: `tests/unit/validation/test_static_check.py`

**Step 1: Write the failing tests**

```python
from video_agent.validation.static_check import StaticCheckValidator


def test_static_check_blocks_subprocess_usage() -> None:
    code = "import subprocess\nsubprocess.run(['rm', '-rf', '/'])"
    report = StaticCheckValidator().validate(code)
    assert report.passed is False
    assert report.issues[0].code == "forbidden_import"
```

```python
from video_agent.adapters.llm.prompt_builder import build_generation_prompt


def test_prompt_builder_includes_prompt_and_output_profile() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"width": 1280, "height": 720},
        feedback=None,
    )
    assert "draw a circle" in prompt
    assert "1280" in prompt
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/adapters/llm/test_prompt_builder.py tests/unit/validation/test_static_check.py -q`
Expected: FAIL with missing modules

**Step 3: Write minimal implementation**

Implement:
- `LLMClient` protocol with `generate_script(prompt_text) -> str`
- `StubLLMClient` for deterministic tests
- prompt builder that merges `prompt`, `style_hints`, `feedback`, `output_profile`
- static checks for AST parseability, forbidden imports, forbidden calls, scene presence

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/adapters/llm/test_prompt_builder.py tests/unit/validation/test_static_check.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/llm/client.py src/video_agent/adapters/llm/prompt_builder.py src/video_agent/validation/static_check.py tests/unit/adapters/llm/test_prompt_builder.py tests/unit/validation/test_static_check.py
git commit -m "feat: add prompt builder and static safety checks"
```

### Task 9: Implement Manim runner and hard validation

**Files:**
- Create: `src/video_agent/adapters/rendering/manim_runner.py`
- Create: `src/video_agent/validation/hard_validation.py`
- Create: `tests/integration/test_render_and_hard_validation.py`

**Step 1: Write the failing integration test**

```python
from video_agent.validation.hard_validation import HardValidator


def test_rendered_video_passes_hard_validation(rendered_circle_artifact) -> None:
    report = HardValidator().validate(rendered_circle_artifact.video_path)
    assert report.passed is True
    assert report.video_metadata.width > 0
    assert report.video_metadata.duration_seconds > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_render_and_hard_validation.py -q`
Expected: FAIL because rendering helper and validator do not exist

**Step 3: Write minimal implementation**

Implement:
- `ManimRunner.render(script_path, output_dir)` via host `subprocess`
- capture `stdout`, `stderr`, exit code, duration
- `HardValidator.validate(video_path)` using `ffprobe`
- output checks: file exists, codec probe works, width/height > 0, duration > 0

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_render_and_hard_validation.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/rendering/manim_runner.py src/video_agent/validation/hard_validation.py tests/integration/test_render_and_hard_validation.py
git commit -m "feat: add manim rendering and hard validation"
```

---

## Week 4 - 抽帧、规则校验、完成判定

**目标：** 从“能渲染”升级到“能做基础质量判断并输出结构化验证报告”。

**本周退出标准：**
1. 成功任务能产出关键帧资源。
2. 可以识别至少 3 类规则问题：黑屏、长静止、编码异常。
3. `completed` 的判定只由结构化报告驱动。

### Task 10: Implement frame extraction and rule validation

**Files:**
- Create: `src/video_agent/adapters/rendering/frame_extractor.py`
- Create: `src/video_agent/validation/rule_validation.py`
- Create: `tests/integration/test_frame_and_rule_validation.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.validation.rule_validation import RuleValidator


def test_frame_extractor_outputs_preview_images(rendered_circle_artifact, frame_extractor) -> None:
    frames = frame_extractor.extract(rendered_circle_artifact.video_path)
    assert len(frames) >= 1
    assert frames[0].suffix == ".png"


def test_rule_validator_detects_black_video(black_video_path) -> None:
    report = RuleValidator().validate(black_video_path)
    assert report.passed is False
    assert any(issue.code == "black_frames" for issue in report.issues)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_frame_and_rule_validation.py -q`
Expected: FAIL with missing extractor/validator

**Step 3: Write minimal implementation**

Implement:
- frame extraction using `ffmpeg` at fixed timestamps or percentage buckets
- rule checks for black frames, frozen tail, unreadable/corrupt file
- normalized issue codes and severity fields

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_frame_and_rule_validation.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/rendering/frame_extractor.py src/video_agent/validation/rule_validation.py tests/integration/test_frame_and_rule_validation.py
git commit -m "feat: add preview extraction and rule validation"
```

### Task 11: Implement validation report aggregation and workflow decisions

**Files:**
- Modify: `src/video_agent/domain/validation_models.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/mcp_resources.py`
- Create: `tests/integration/test_workflow_completion.py`

**Step 1: Write the failing integration tests**

```python

def test_task_becomes_completed_only_after_validation_passes(app_context, completed_render_fixture) -> None:
    task_id = completed_render_fixture.task_id
    snapshot = app_context.task_service.get_video_task(task_id)
    assert snapshot.status == "completed"
    assert snapshot.latest_validation_summary["passed"] is True


def test_get_video_result_returns_artifacts_for_completed_task(app_context, completed_render_fixture) -> None:
    result = app_context.task_service.get_video_result(completed_render_fixture.task_id)
    assert result.video_resource.endswith("final_video.mp4")
    assert len(result.preview_frame_resources) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_workflow_completion.py -q`
Expected: FAIL because completion logic is incomplete

**Step 3: Write minimal implementation**

Implement:
- aggregated `ValidationReport` with hard/rule sections
- workflow decisions: `completed`, `revising`, `failed`
- validation report persistence in DB + filesystem
- resource resolution for `task.json`, `validation_report.json`, `current_script.py`, `final_video.mp4`, previews

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_workflow_completion.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/domain/validation_models.py src/video_agent/application/workflow_engine.py src/video_agent/application/task_service.py src/video_agent/server/mcp_resources.py tests/integration/test_workflow_completion.py
git commit -m "feat: drive task completion from validation reports"
```

---

## Week 5 - Revision lineage、取消任务、结果继承

**目标：** 让系统不只是“一次性生成”，而是能基于已有结果继续修订，同时保留 lineage 和最佳结果索引。

**本周退出标准：**
1. `revise_video_task` 会创建 child task，而不是覆盖原任务。
2. `cancel_video_task` 能对 queued/running 任务生效。
3. 子任务能继承父任务的 prompt、最佳脚本引用、验证摘要。

### Task 12: Implement revision service and lineage persistence

**Files:**
- Create: `src/video_agent/application/revision_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Create: `tests/integration/test_revision_and_cancel.py`

**Step 1: Write the failing tests**

```python

def test_revise_task_creates_child_task(task_service) -> None:
    parent = task_service.create_video_task(prompt="draw a circle", idempotency_key="parent")
    child = task_service.revise_video_task(parent.task_id, feedback="make it blue")
    snapshot = task_service.get_video_task(child.task_id)

    assert snapshot.parent_task_id == parent.task_id
    assert snapshot.root_task_id == parent.task_id
    assert snapshot.status == "queued"


def test_revision_inherits_parent_context(task_service, completed_task) -> None:
    child = task_service.revise_video_task(completed_task.task_id, feedback="add title")
    snapshot = task_service.get_video_task(child.task_id)
    assert snapshot.inherited_from_task_id == completed_task.task_id
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_revision_and_cancel.py -q`
Expected: FAIL because revise flow is missing

**Step 3: Write minimal implementation**

Implement:
- `RevisionService.create_revision(base_task_id, feedback, preserve_working_parts)`
- child task creation with `parent_task_id`, `root_task_id`
- inheritance of latest successful script artifact reference
- event logging for `revision_created`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_revision_and_cancel.py -q`
Expected: PASS for revision tests

**Step 5: Commit**

```bash
git add src/video_agent/application/revision_service.py src/video_agent/application/task_service.py src/video_agent/adapters/storage/sqlite_store.py tests/integration/test_revision_and_cancel.py
git commit -m "feat: add revision lineage support"
```

### Task 13: Add cancel tool and cancellation-aware worker behavior

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/worker/worker_loop.py`
- Modify: `tests/integration/test_revision_and_cancel.py`

**Step 1: Write the failing tests**

```python

def test_cancel_task_marks_queued_task_as_cancelled(task_service) -> None:
    created = task_service.create_video_task(prompt="draw a circle", idempotency_key="cancel-q")
    task_service.cancel_video_task(created.task_id)
    snapshot = task_service.get_video_task(created.task_id)
    assert snapshot.status == "cancelled"


def test_worker_stops_processing_cancelled_task(app_context) -> None:
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="cancel-r")
    app_context.task_service.cancel_video_task(created.task_id)
    processed = app_context.worker.run_once()
    assert processed == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_revision_and_cancel.py -q`
Expected: FAIL because cancellation is not implemented

**Step 3: Write minimal implementation**

Implement:
- `cancel_video_task` tool
- task status transition guardrails
- worker pre-flight cancellation check
- cancellation event + standardized error payload (`error_type="cancelled"`)

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_revision_and_cancel.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/mcp_tools.py src/video_agent/application/task_service.py src/video_agent/application/workflow_engine.py src/video_agent/worker/worker_loop.py tests/integration/test_revision_and_cancel.py
git commit -m "feat: add task cancellation flow"
```

---

## Week 6 - 安全加固、可观测性、E2E 与发布准备

**目标：** 在已有闭环上补齐安全边界、日志与端到端验证，形成可演示、可调试、可继续扩展的 v1。

**本周退出标准：**
1. 有 1 条从 `create_video_task` 到 `get_video_result` 的 e2e 测试。
2. 危险脚本、渲染失败、验证失败至少各有 1 条标准化错误对象。
3. README 和本地 runbook 足够让第二个开发者在半天内跑起来。

### Task 14: Add runtime policy, structured logging, and metrics

**Files:**
- Create: `src/video_agent/safety/runtime_policy.py`
- Create: `src/video_agent/observability/logging.py`
- Create: `src/video_agent/observability/metrics.py`
- Create: `tests/unit/safety/test_runtime_policy.py`

**Step 1: Write the failing tests**

```python
from video_agent.safety.runtime_policy import RuntimePolicy


def test_runtime_policy_rejects_non_whitelisted_paths(tmp_path) -> None:
    policy = RuntimePolicy(work_root=tmp_path)
    assert policy.is_allowed_write(tmp_path / "task" / "script.py") is True
    assert policy.is_allowed_write(tmp_path.parent / "escape.txt") is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/safety/test_runtime_policy.py -q`
Expected: FAIL because runtime policy is missing

**Step 3: Write minimal implementation**

Implement:
- path allowlist checks
- render timeout defaults
- structured log helpers with `task_id`, `phase`, `attempt_count`
- simple counters/timers for `generation`, `render`, `validation`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/safety/test_runtime_policy.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/safety/runtime_policy.py src/video_agent/observability/logging.py src/video_agent/observability/metrics.py tests/unit/safety/test_runtime_policy.py
git commit -m "feat: add runtime safety policy and observability"
```

### Task 15: Add end-to-end test, final docs, and release checklist

**Files:**
- Create: `tests/e2e/test_single_task_flow.py`
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`
- Create: `docs/runbooks/release-checklist.md`

**Step 1: Write the failing e2e test**

```python

def test_single_task_flow(app_context) -> None:
    created = app_context.task_service.create_video_task(prompt="draw a labeled blue circle", idempotency_key="e2e")
    while True:
        processed = app_context.worker.run_once()
        snapshot = app_context.task_service.get_video_task(created.task_id)
        if snapshot.status in {"completed", "failed"}:
            break
        assert processed in {0, 1}

    assert snapshot.status == "completed"
    result = app_context.task_service.get_video_result(created.task_id)
    assert result.video_resource.endswith("final_video.mp4")
    assert len(result.preview_frame_resources) >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_single_task_flow.py -q`
Expected: FAIL until full pipeline is wired end-to-end

**Step 3: Write minimal implementation and docs updates**

Update docs with:
- how to install Manim/ffmpeg
- how to run MCP server locally
- how to start worker locally
- how to inspect `data/tasks/<task_id>/`
- what a passing validation report looks like
- release checklist for demo readiness

**Step 4: Run the final verification suite**

Run: `pytest tests/unit -q && pytest tests/integration -q && pytest tests/e2e/test_single_task_flow.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/e2e/test_single_task_flow.py README.md docs/runbooks/local-dev.md docs/runbooks/release-checklist.md
git commit -m "test: add e2e coverage and release docs"
```

---

## 每周节奏建议

每周按以下固定节奏推进，避免后期返工：
1. 周一：先补 failing tests，定义本周 schema / 接口边界。
2. 周二到周三：只做最小实现，不扩 scope。
3. 周四：补 integration/e2e，清理命名和目录结构。
4. 周五：只做验证、文档、演示脚本，不继续加新功能。

## 全局验收标准

到第 6 周结束时，v1 必须满足：
1. 可以通过 MCP 创建任务并拿到 `task_id`。
2. worker 能异步推进任务到 `completed | failed | cancelled`。
3. `get_video_task` 能返回结构化快照和验证摘要。
4. `get_video_result` 能返回视频、脚本、关键帧、验证报告引用。
5. `revise_video_task` 会创建 child task 并保留 lineage。
6. 危险脚本会被拦截，不直接进入渲染。
7. 至少有 1 条 happy path e2e 测试稳定通过。

## 不做事项（直到 v1 完成）

以下内容在本计划内明确不做：
1. 多模型路由与自动比较。
2. 云对象存储、远程队列、分布式 worker。
3. Web UI、时间轴编辑器、多人协作。
4. 配音、字幕、配乐、素材库。
5. 高级视觉语义评分器；v1 先以硬校验 + 规则校验为主。
