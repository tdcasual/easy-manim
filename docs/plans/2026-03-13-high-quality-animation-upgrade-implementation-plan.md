# High Quality Animation Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise the system from "reliably produces valid Manim videos" to "more consistently produces visually strong explanatory animations" within two weeks, without changing the local-first MCP + worker architecture.

**Architecture:** Keep the existing `FastMCP -> TaskService -> WorkflowEngine -> ManimRunner -> validators` pipeline intact. Add three focused layers on top of it: configurable production render quality, a deterministic scene-planning layer that enriches prompts before code generation, and lightweight preview-based visual QA that can fail bad-looking outputs and feed targeted repair. Extend the evaluation slice so quality improvements are measured separately from pure pipeline health.

**Tech Stack:** Python 3.10+, `pydantic`, `FastMCP`, SQLite, `pytest`, `Pillow`, Manim Community, ffmpeg/ffprobe, existing local evaluation tooling

---

## Recommended implementation shape

**Recommended: deterministic scene planner + richer prompting**
- Build a local `ScenePlan` from `prompt`, `output_profile`, and `style_hints`
- Persist the plan as an artifact
- Feed the plan into prompt generation, render settings, and visual QA

**Why this is the right two-week choice**
- avoids adding a second LLM call and a second failure mode
- immediately improves routing for formula scenes, camera scenes, and pacing defaults
- stays compatible with the current stub and real-provider setup

**Alternative A: separate LLM planning pass**
- stronger upside later
- too much risk for two weeks because it expands provider behavior, retries, and tests at the same time

**Alternative B: template-only scene presets**
- easier to implement
- improves consistency but does not generalize well enough beyond a few canned scenes

---

### Task 1: Add production-grade render quality controls

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/adapters/rendering/manim_runner.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `tests/integration/test_validation_profiles.py`
- Create: `tests/integration/test_render_quality_profiles.py`
- Docs: `docs/runbooks/local-dev.md`
- Docs: `docs/runbooks/beta-ops.md`

**Step 1: Write the failing integration test**

In `tests/integration/test_render_quality_profiles.py` add:

```python
import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    invocation_log = tmp_path / "manim_invocation.json"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        f"printf '%s' \"$@\" > \"{invocation_log}\"\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/1080p60\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/1080p60/$7\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    _write_executable(
        fake_ffprobe,
        "#!/bin/sh\n"
        "printf '%s' '{\"streams\": [{\"codec_type\": \"video\", \"width\": 1920, \"height\": 1080}], \"format\": {\"duration\": \"6.0\"}}'\n",
    )

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command=str(fake_manim),
        ffmpeg_command=str(fake_ffmpeg),
        ffprobe_command=str(fake_ffprobe),
    )


def test_output_profile_can_request_production_quality_render(tmp_path: Path) -> None:
    app = create_app_context(_build_settings(tmp_path))
    created = app.task_service.create_video_task(
        prompt="draw a blue circle",
        output_profile={"quality_preset": "production"},
    )

    app.worker.run_once()

    command_line = (tmp_path / "manim_invocation.json").read_text()
    assert "-qh" in command_line
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/integration/test_render_quality_profiles.py -q`

Expected: FAIL because `ManimRunner` hardcodes `-ql` and ignores `output_profile`.

**Step 3: Write minimal implementation**

In `src/video_agent/config.py` add settings like:

```python
default_quality_preset: str = "development"
default_frame_rate: int | None = None
default_pixel_width: int | None = None
default_pixel_height: int | None = None
```

In `src/video_agent/server/main.py` read env vars such as:

```python
default_quality_preset=os.getenv("EASY_MANIM_DEFAULT_QUALITY_PRESET", "development"),
default_frame_rate=_env_optional_int("EASY_MANIM_DEFAULT_FRAME_RATE"),
default_pixel_width=_env_optional_int("EASY_MANIM_DEFAULT_PIXEL_WIDTH"),
default_pixel_height=_env_optional_int("EASY_MANIM_DEFAULT_PIXEL_HEIGHT"),
```

In `src/video_agent/adapters/rendering/manim_runner.py` update `render()` to accept a render profile:

```python
def render(
    self,
    script_path: Path,
    output_dir: Path,
    *,
    quality_preset: str = "development",
    frame_rate: int | None = None,
    pixel_width: int | None = None,
    pixel_height: int | None = None,
    ...
) -> RenderResult:
    quality_flag = {"development": "-ql", "preview": "-qm", "production": "-qh"}[quality_preset]
    command = [
        self.command,
        quality_flag,
        str(script_path),
        scene_name,
        "--media_dir",
        str(output_dir),
        "-o",
        output_name,
    ]
    if frame_rate is not None:
        command.extend(["--frame_rate", str(frame_rate)])
    if pixel_width is not None:
        command.extend(["--pixel_width", str(pixel_width)])
    if pixel_height is not None:
        command.extend(["--pixel_height", str(pixel_height)])
```

In `src/video_agent/application/workflow_engine.py` derive the effective render settings from `task.output_profile` first, then fall back to `settings`.

**Step 4: Run focused tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/integration/test_render_quality_profiles.py tests/integration/test_validation_profiles.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/config.py src/video_agent/server/main.py src/video_agent/adapters/rendering/manim_runner.py src/video_agent/application/workflow_engine.py tests/integration/test_render_quality_profiles.py tests/integration/test_validation_profiles.py docs/runbooks/local-dev.md docs/runbooks/beta-ops.md
git commit -m "feat: add configurable production render quality"
```

---

### Task 2: Add a deterministic scene planner and prompt enrichment

**Files:**
- Create: `src/video_agent/application/scene_plan.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/adapters/llm/prompt_builder.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/unit/application/test_scene_plan.py`
- Test: `tests/unit/adapters/llm/test_prompt_builder.py`
- Test: `tests/integration/test_mcp_tools.py`
- Test: `tests/integration/test_workflow_completion.py`

**Step 1: Write the failing tests**

In `tests/unit/application/test_scene_plan.py` add:

```python
from video_agent.application.scene_plan import build_scene_plan


def test_build_scene_plan_routes_formula_prompt_to_mathtex_profile() -> None:
    plan = build_scene_plan(
        prompt="show the quadratic formula and highlight the discriminant",
        output_profile={"quality_preset": "production"},
        style_hints={"tone": "teaching"},
    )

    assert plan.scene_class == "Scene"
    assert plan.formula_strategy == "mathtex_focus"
    assert plan.sections[0].goal
    assert "TransformMatchingTex" in plan.animation_recipes
```

Extend `tests/unit/adapters/llm/test_prompt_builder.py` with:

```python
from video_agent.application.scene_plan import ScenePlan, ScenePlanSection


def test_prompt_builder_includes_scene_plan_and_style_hints() -> None:
    plan = ScenePlan(
        scene_class="MovingCameraScene",
        formula_strategy="none",
        transition_style="lagged",
        camera_strategy="auto_zoom",
        animation_recipes=["LaggedStart", "AnimationGroup"],
        sections=[ScenePlanSection(name="intro", goal="introduce the main shape")],
    )
    prompt = build_generation_prompt(
        prompt="show a labeled axis animation",
        output_profile={"quality_preset": "production"},
        feedback=None,
        style_hints={"tone": "clean"},
        scene_plan=plan,
    )
    assert "MovingCameraScene" in prompt
    assert "auto_zoom" in prompt
    assert "LaggedStart" in prompt
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py -q`

Expected: FAIL because there is no scene-plan module and the prompt builder has no `scene_plan` support.

**Step 3: Write minimal implementation**

Create `src/video_agent/application/scene_plan.py` with:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class ScenePlanSection(BaseModel):
    name: str
    goal: str


class ScenePlan(BaseModel):
    scene_class: str = "Scene"
    formula_strategy: str = "none"
    transition_style: str = "succession"
    camera_strategy: str = "static"
    animation_recipes: list[str] = Field(default_factory=list)
    sections: list[ScenePlanSection] = Field(default_factory=list)


def build_scene_plan(
    prompt: str,
    output_profile: dict[str, object] | None = None,
    style_hints: dict[str, object] | None = None,
) -> ScenePlan:
    text = prompt.lower()
    plan = ScenePlan()
    if "formula" in text or "mathtex" in text:
        plan.formula_strategy = "mathtex_focus"
        plan.animation_recipes.append("TransformMatchingTex")
    if "zoom" in text or "highlight" in text or "focus" in text:
        plan.scene_class = "MovingCameraScene"
        plan.camera_strategy = "auto_zoom"
    if "axis" in text or "graph" in text:
        plan.animation_recipes.extend(["LaggedStart", "AnimationGroup"])
    plan.sections = [ScenePlanSection(name="main", goal=prompt)]
    return plan
```

Modify `src/video_agent/domain/models.py` and `src/video_agent/application/task_service.py` so `create_video_task()` accepts and stores:

```python
style_hints: dict[str, Any] = Field(default_factory=dict)
```

Expose `style_hints` through `src/video_agent/server/fastmcp_server.py` and `src/video_agent/server/mcp_tools.py`.

In `src/video_agent/adapters/storage/artifact_store.py` add:

```python
def scene_plan_path(self, task_id: str) -> Path:
    return self.task_dir(task_id) / "artifacts" / "scene_plan.json"

def write_scene_plan(self, task_id: str, payload: dict[str, Any]) -> Path:
    target = self.scene_plan_path(task_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2))
    return target
```

In `src/video_agent/adapters/llm/prompt_builder.py` extend the prompt:

```python
def build_generation_prompt(..., style_hints=None, scene_plan=None) -> str:
    ...
    if style_hints:
        lines.append(f"Style hints: {style_hints}")
    if scene_plan:
        lines.append(f"Scene class: {scene_plan.scene_class}")
        lines.append(f"Camera strategy: {scene_plan.camera_strategy}")
        lines.append(f"Transition style: {scene_plan.transition_style}")
        lines.append(f"Animation recipes: {scene_plan.animation_recipes}")
        lines.append(f"Sections: {[section.model_dump(mode='json') for section in scene_plan.sections]}")
```

In `src/video_agent/application/workflow_engine.py`, build and persist the scene plan before generation, then pass it into `build_generation_prompt()`.

**Step 4: Run focused tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py tests/integration/test_mcp_tools.py tests/integration/test_workflow_completion.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/scene_plan.py src/video_agent/domain/models.py src/video_agent/application/task_service.py src/video_agent/server/fastmcp_server.py src/video_agent/server/mcp_tools.py src/video_agent/adapters/storage/artifact_store.py src/video_agent/adapters/llm/prompt_builder.py src/video_agent/application/workflow_engine.py tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py tests/integration/test_mcp_tools.py tests/integration/test_workflow_completion.py
git commit -m "feat: add deterministic scene planning and prompt enrichment"
```

---

### Task 3: Add lightweight preview-based visual QA

**Files:**
- Modify: `pyproject.toml`
- Create: `src/video_agent/validation/preview_quality.py`
- Modify: `src/video_agent/domain/validation_models.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/failure_context.py`
- Test: `tests/unit/validation/test_preview_quality.py`
- Test: `tests/integration/test_frame_and_rule_validation.py`
- Test: `tests/integration/test_workflow_completion.py`
- Docs: `docs/runbooks/beta-ops.md`

**Step 1: Write the failing tests**

Create `tests/unit/validation/test_preview_quality.py`:

```python
from pathlib import Path

from PIL import Image

from video_agent.validation.preview_quality import PreviewQualityValidator


def _solid(path: Path, rgb: tuple[int, int, int]) -> None:
    Image.new("RGB", (320, 180), rgb).save(path)


def test_preview_quality_flags_near_blank_sequence(tmp_path: Path) -> None:
    frame_a = tmp_path / "frame_001.png"
    frame_b = tmp_path / "frame_002.png"
    _solid(frame_a, (0, 0, 0))
    _solid(frame_b, (0, 0, 0))

    report = PreviewQualityValidator().validate([frame_a, frame_b], profile={})

    assert report.passed is False
    assert any(issue.code == "near_blank_preview" for issue in report.issues)


def test_preview_quality_flags_static_sequence(tmp_path: Path) -> None:
    frame_a = tmp_path / "frame_001.png"
    frame_b = tmp_path / "frame_002.png"
    _solid(frame_a, (200, 200, 200))
    _solid(frame_b, (200, 200, 200))

    report = PreviewQualityValidator().validate([frame_a, frame_b], profile={"check_static_previews": True})

    assert any(issue.code == "static_previews" for issue in report.issues)
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/validation/test_preview_quality.py -q`

Expected: FAIL because there is no preview-quality validator and `Pillow` is not installed.

**Step 3: Write minimal implementation**

In `pyproject.toml` add:

```toml
"Pillow>=10,<12",
```

Create `src/video_agent/validation/preview_quality.py`:

```python
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from video_agent.domain.enums import ValidationDecision
from video_agent.domain.validation_models import ValidationIssue, ValidationReport


class PreviewQualityValidator:
    def validate(self, preview_paths: list[Path], profile: dict[str, object] | None = None) -> ValidationReport:
        issues: list[ValidationIssue] = []
        effective = profile or {}
        if not preview_paths:
            issues.append(ValidationIssue(code="missing_previews", message="No preview frames were extracted"))
            return ValidationReport(decision=ValidationDecision.FAIL, passed=False, issues=issues)

        images = [Image.open(path).convert("RGB") for path in preview_paths]
        first_brightness = sum(ImageStat.Stat(images[0]).mean) / 3.0
        if effective.get("check_blank_previews", True) and first_brightness < 5.0:
            issues.append(ValidationIssue(code="near_blank_preview", message="Preview sequence starts effectively blank"))

        if effective.get("check_static_previews", True) and len(images) >= 2:
            diff = ImageChops.difference(images[0], images[-1])
            if sum(ImageStat.Stat(diff).mean) / 3.0 < 1.0:
                issues.append(ValidationIssue(code="static_previews", message="Preview sequence shows too little motion"))

        passed = not issues
        return ValidationReport(
            decision=ValidationDecision.PASS if passed else ValidationDecision.FAIL,
            passed=passed,
            issues=issues,
        )
```

In `src/video_agent/application/workflow_engine.py`, run the preview validator after frame extraction and combine it with hard + file-based rule validation. In `src/video_agent/application/failure_context.py`, persist preview issue codes into `failure_context.json` so targeted repair can reference them.

**Step 4: Run focused tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/validation/test_preview_quality.py tests/integration/test_frame_and_rule_validation.py tests/integration/test_workflow_completion.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/video_agent/validation/preview_quality.py src/video_agent/domain/validation_models.py src/video_agent/application/workflow_engine.py src/video_agent/application/failure_context.py tests/unit/validation/test_preview_quality.py tests/integration/test_frame_and_rule_validation.py tests/integration/test_workflow_completion.py docs/runbooks/beta-ops.md
git commit -m "feat: add preview based visual quality validation"
```

---

### Task 4: Add a quality-focused evaluation slice and release signal

**Files:**
- Modify: `evals/beta_prompt_suite.json`
- Create: `src/video_agent/evaluation/quality_reporting.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/evaluation/reporting.py`
- Modify: `src/video_agent/eval/main.py`
- Test: `tests/unit/evaluation/test_quality_reporting.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Docs: `docs/runbooks/beta-ops.md`
- Docs: `docs/runbooks/release-checklist.md`

**Step 1: Write the failing tests**

Create `tests/unit/evaluation/test_quality_reporting.py`:

```python
from video_agent.evaluation.quality_reporting import build_quality_report


def test_build_quality_report_summarizes_quality_slice() -> None:
    report = build_quality_report(
        [
            {"tags": ["quality"], "status": "completed", "quality_score": 0.9, "quality_issue_codes": []},
            {"tags": ["quality"], "status": "failed", "quality_score": 0.2, "quality_issue_codes": ["static_previews"]},
        ]
    )

    assert report["case_count"] == 2
    assert report["pass_rate"] == 0.5
    assert report["median_quality_score"] == 0.55
    assert report["quality_issue_codes"]["static_previews"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_quality_reporting.py tests/integration/test_eval_run_cli.py -q`

Expected: FAIL because there is no quality-reporting module and evaluation output has no quality slice.

**Step 3: Write minimal implementation**

Expand `evals/beta_prompt_suite.json` with quality-tagged cases such as:

```json
{
  "case_id": "quality-formula-focus",
  "prompt": "show the quadratic formula, zoom into the discriminant, and keep the layout readable",
  "tags": ["quality", "formula", "real-provider"]
}
```

Create `src/video_agent/evaluation/quality_reporting.py`:

```python
from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any


def build_quality_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    quality_items = [item for item in items if "quality" in (item.get("tags") or [])]
    scores = [float(item.get("quality_score", 0.0)) for item in quality_items]
    failures = Counter(
        code
        for item in quality_items
        for code in item.get("quality_issue_codes", [])
    )
    passed = sum(1 for item in quality_items if item.get("status") == "completed")
    total = len(quality_items)
    return {
        "case_count": total,
        "pass_rate": (passed / total) if total else 0.0,
        "median_quality_score": median(scores) if scores else 0.0,
        "quality_issue_codes": dict(failures),
    }
```

In `src/video_agent/application/eval_service.py`, add `quality_issue_codes` and `quality_score` to each item by reading validation issue codes from `latest_validation_summary`. In `src/video_agent/evaluation/reporting.py`, append a `quality` section beside the existing repair section. In `src/video_agent/eval/main.py`, include the quality summary in text output.

**Step 4: Run focused tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_quality_reporting.py tests/integration/test_eval_run_cli.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add evals/beta_prompt_suite.json src/video_agent/evaluation/quality_reporting.py src/video_agent/application/eval_service.py src/video_agent/evaluation/reporting.py src/video_agent/eval/main.py tests/unit/evaluation/test_quality_reporting.py tests/integration/test_eval_run_cli.py docs/runbooks/beta-ops.md docs/runbooks/release-checklist.md
git commit -m "feat: add quality focused evaluation reporting"
```

---

## Two-week execution order

### Week 1
- Task 1: production-grade render quality controls
- Task 2: deterministic scene planner and prompt enrichment

### Week 2
- Task 3: preview-based visual QA
- Task 4: quality-focused evaluation slice and release signal

## Success criteria

- Default production jobs can render at high-quality settings instead of fixed low-quality settings
- Prompts contain explicit scene structure, camera intent, and animation recipes
- The pipeline can reject clearly blank or static outputs based on preview frames
- Evaluation summaries distinguish pipeline success from visual quality success
- Quality-tagged runs can be tracked independently from smoke and repair runs

## Final verification sequence

```bash
source .venv/bin/activate
python -m pytest tests/integration/test_render_quality_profiles.py -q
python -m pytest tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py -q
python -m pytest tests/unit/validation/test_preview_quality.py tests/integration/test_frame_and_rule_validation.py -q
python -m pytest tests/unit/evaluation/test_quality_reporting.py tests/integration/test_eval_run_cli.py -q
python -m pytest -q
python scripts/beta_smoke.py --mode ci
```
