# Formula Animation Safety Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise the live `real-provider + quality` formula slice from 0.8 overall / formula-case failure to a stable pass by removing a known brittle MathTex generation pattern and adding a cheap pre-render guardrail.

**Architecture:** Keep the current `ScenePlan -> prompt_builder -> LLM -> static check -> render -> preview quality` pipeline. Fix the problem at the source by changing the formula-scene plan and prompt so the model prefers symbolic selection and non-destructive emphasis, then add a static validator/diagnostic rule that blocks `TransformMatchingTex` calls fed by numeric MathTex slices before render. This keeps the system local-first, preserves provider flexibility, and improves both first-pass quality and repair quality.

**Tech Stack:** Python 3.10+, `ast`, `pydantic`, `pytest`, Manim Community, existing eval CLI and beta suite

---

## Recommended implementation shape

**Recommended: prompt guidance plus static guardrail**
- Stop nudging formula prompts toward `TransformMatchingTex` as the default emphasis tool.
- Add explicit prompt instructions to prefer `get_part_by_tex`, `set_color_by_tex`, `Indicate`, and `SurroundingRectangle`.
- Block numeric-slice `TransformMatchingTex` patterns before render so the system fails fast and feeds cleaner repair context.

**Why this is the right next move**
- matches the actual failing live script instead of making a generic “quality” change
- uses official Manim behavior as the source of truth: `TransformMatchingTex` works best on whole compatible expressions, while `MathTex` already exposes symbolic selection helpers
- adds a second safety layer, so one bad provider sample does not immediately become a render crash

**Alternative A: prompt-only**
- fastest patch
- improves first-pass generation, but still leaves the pipeline exposed to future provider drift

**Alternative B: formula template scenes**
- strongest short-term reliability
- too restrictive for the broader goal of a flexible animation agent, and likely harms coverage on varied math prompts

---

### Task 1: Lock the failure into tests before changing behavior

**Files:**
- Modify: `tests/unit/application/test_scene_plan.py`
- Modify: `tests/unit/adapters/llm/test_prompt_builder.py`

**Step 1: Write the failing scene-plan test**

In `tests/unit/application/test_scene_plan.py` add:

```python
def test_build_scene_plan_adds_formula_safety_guidance() -> None:
    plan = build_scene_plan(
        prompt="show the quadratic formula and highlight the discriminant",
        output_profile={"quality_preset": "production"},
        style_hints={"tone": "teaching"},
    )

    assert plan.formula_strategy == "mathtex_focus"
    assert "Indicate" in plan.animation_recipes
    assert "SurroundingRectangle" in plan.animation_recipes
    assert "TransformMatchingTex" not in plan.animation_recipes
    assert "avoid_numeric_mathtex_slices" in plan.quality_directives
    assert "prefer_symbolic_tex_selection" in plan.quality_directives
    assert "prefer_non_destructive_formula_emphasis" in plan.quality_directives
    assert "only_transform_matching_full_expressions" in plan.quality_directives
```

**Step 2: Write the failing prompt-builder test**

In `tests/unit/adapters/llm/test_prompt_builder.py` add:

```python
def test_prompt_builder_expands_formula_safety_requirements() -> None:
    plan = ScenePlan(
        scene_class="Scene",
        formula_strategy="mathtex_focus",
        transition_style="lagged",
        camera_strategy="static",
        pacing_strategy="measured",
        animation_recipes=["Indicate", "SurroundingRectangle"],
        quality_directives=[
            "avoid_numeric_mathtex_slices",
            "prefer_symbolic_tex_selection",
            "prefer_non_destructive_formula_emphasis",
            "only_transform_matching_full_expressions",
        ],
        sections=[ScenePlanSection(name="focus", goal="Highlight the discriminant")],
    )

    prompt = build_generation_prompt(
        prompt="show the quadratic formula and focus on the discriminant",
        output_profile={"quality_preset": "production"},
        feedback=None,
        style_hints={"tone": "teaching"},
        scene_plan=plan,
    )

    assert "Do not isolate MathTex content with fixed numeric indices" in prompt
    assert "`get_part_by_tex`" in prompt
    assert "`set_color_by_tex`" in prompt
    assert "`Indicate`" in prompt
    assert "`SurroundingRectangle`" in prompt
    assert "Use `TransformMatchingTex` only between full `MathTex` expressions" in prompt
```

**Step 3: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py -q`

Expected: FAIL because the planner still recommends `TransformMatchingTex`, and the prompt builder does not yet include formula-safety instructions.

**Step 4: Commit**

```bash
git add tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py
git commit -m "test: lock formula animation safety guidance"
```

---

### Task 2: Change formula planning and prompting to prefer safe emphasis patterns

**Files:**
- Modify: `src/video_agent/application/scene_plan.py`
- Modify: `src/video_agent/adapters/llm/prompt_builder.py`
- Test: `tests/unit/application/test_scene_plan.py`
- Test: `tests/unit/adapters/llm/test_prompt_builder.py`

**Step 1: Update the scene planner**

In `src/video_agent/application/scene_plan.py`, change the formula branch from:

```python
plan.animation_recipes.append("TransformMatchingTex")
```

to:

```python
plan.animation_recipes.extend(["Indicate", "SurroundingRectangle"])
plan.quality_directives.extend(
    [
        "avoid_numeric_mathtex_slices",
        "prefer_symbolic_tex_selection",
        "prefer_non_destructive_formula_emphasis",
        "only_transform_matching_full_expressions",
    ]
)
```

Keep `keep_formula_large_and_centered` and `hold_focus_before_transition` as-is.

**Step 2: Expand the prompt-builder instructions**

In `src/video_agent/adapters/llm/prompt_builder.py`, add mappings like:

```python
"avoid_numeric_mathtex_slices": (
    "Do not isolate MathTex or Tex content with fixed numeric indices such as "
    "`expr[0][9:18]` or similar slice-based submobject access."
),
"prefer_symbolic_tex_selection": (
    "When selecting part of a formula, prefer symbolic helpers such as "
    "`substrings_to_isolate`, `get_part_by_tex`, `get_parts_by_tex`, or `set_color_by_tex`."
),
"prefer_non_destructive_formula_emphasis": (
    "For formula emphasis, prefer non-destructive highlighting such as `Indicate`, "
    "`SurroundingRectangle`, or `set_color_by_tex` before creating a separate term mobject."
),
"only_transform_matching_full_expressions": (
    "Use `TransformMatchingTex` only between full `MathTex` expressions with compatible tokenization, "
    "not on arbitrary indexed slices of another expression."
),
```

**Step 3: Run focused tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py -q`

Expected: PASS

**Step 4: Commit**

```bash
git add src/video_agent/application/scene_plan.py src/video_agent/adapters/llm/prompt_builder.py tests/unit/application/test_scene_plan.py tests/unit/adapters/llm/test_prompt_builder.py
git commit -m "feat: add formula-safe planning and prompt guidance"
```

---

### Task 3: Add a pre-render guardrail for unsafe `TransformMatchingTex` usage

**Files:**
- Modify: `src/video_agent/validation/static_check.py`
- Modify: `src/video_agent/validation/script_diagnostics.py`
- Modify: `src/video_agent/config.py`
- Modify: `tests/unit/validation/test_static_check.py`
- Modify: `tests/unit/validation/test_script_diagnostics.py`

**Step 1: Write the failing static-check test**

In `tests/unit/validation/test_static_check.py` add:

```python
def test_static_check_blocks_transformmatchingtex_numeric_slice_source() -> None:
    code = (
        "from manim import *\\n\\n"
        "class Demo(Scene):\\n"
        "    def construct(self):\\n"
        "        expr = MathTex(r'x = \\\\frac{-b \\\\pm \\\\sqrt{b^2 - 4ac}}{2a}')\\n"
        "        part = MathTex(r'b^2 - 4ac')\\n"
        "        self.play(TransformMatchingTex(expr[0][9:18].copy(), part))\\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "unsafe_transformmatchingtex_slice"
```

Also add a passing case for:

```python
self.play(TransformMatchingTex(old_expr, new_expr))
```

**Step 2: Write the failing diagnostics test**

In `tests/unit/validation/test_script_diagnostics.py` add:

```python
def test_script_diagnostics_accepts_moving_camera_scene_subclass() -> None:
    script = (
        "from manim import MovingCameraScene\\n\\n"
        "class Demo(MovingCameraScene):\\n"
        "    def construct(self):\\n"
        "        pass\\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert diagnostics == []
```

**Step 3: Implement the static validator rule**

In `src/video_agent/validation/static_check.py`, detect calls where:
- call name is `TransformMatchingTex`
- first positional arg contains a numeric `Subscript` or `Slice`

Minimal shape:

```python
elif isinstance(node, ast.Call):
    call_name = self._call_name(node.func)
    if call_name == "TransformMatchingTex" and node.args and self._contains_numeric_subscript(node.args[0]):
        issues.append(
            ValidationIssue(
                code="unsafe_transformmatchingtex_slice",
                message=(
                    "TransformMatchingTex source should not be built from numeric subscript or slice access. "
                    "Prefer full MathTex expressions or symbolic tex selection helpers."
                ),
            )
        )
```

Add helper methods that unwrap `.copy()` calls and recursively inspect for `ast.Subscript` with `ast.Slice`, integer constants, or nested subscripts.

**Step 4: Align script diagnostics with the validator**

In `src/video_agent/validation/script_diagnostics.py`, update `_is_scene_subclass()` so it accepts any base whose name ends with `Scene`, matching the newer static validator behavior.

Also add a diagnostic for the unsafe transform pattern if you can do it cheaply:

```python
ScriptDiagnostic(
    code="unsafe_transformmatchingtex_slice",
    message="TransformMatchingTex is using a numerically indexed tex slice as its source.",
    line=...,
    call_name="TransformMatchingTex",
)
```

If that diagnostic is added, it will improve auto-repair feedback quality without another provider call.

**Step 5: Make the new issue retryable**

In `src/video_agent/config.py`, append:

```python
"unsafe_transformmatchingtex_slice",
```

to `auto_repair_retryable_issue_codes`.

**Step 6: Run focused tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/validation/test_static_check.py tests/unit/validation/test_script_diagnostics.py -q`

Expected: PASS

**Step 7: Commit**

```bash
git add src/video_agent/validation/static_check.py src/video_agent/validation/script_diagnostics.py src/video_agent/config.py tests/unit/validation/test_static_check.py tests/unit/validation/test_script_diagnostics.py
git commit -m "feat: block unsafe formula transform slices before render"
```

---

### Task 4: Prove the fix with the real provider and preserve the regression check

**Files:**
- Modify: `docs/runbooks/real-provider-trial.md`
- Modify: `docs/runbooks/beta-ops.md`
- Optional Test: `tests/integration/test_workflow_completion.py`

**Step 1: Update the runbook**

Add a short note to `docs/runbooks/real-provider-trial.md` and `docs/runbooks/beta-ops.md`:
- formula-scene regressions commonly show up as `render_failed` from unsafe MathTex transforms
- the required verification slice is the AND-filtered `real-provider + quality` suite
- success means `provider-mathtex-formula` passes, not just overall suite health

**Step 2: Run focused integration tests**

Run: `source .venv/bin/activate && python -m pytest tests/integration/test_workflow_completion.py tests/integration/test_eval_run_cli.py -q`

Expected: PASS

**Step 3: Run the live provider slice**

Run:

```bash
source .venv/bin/activate && \
set -a && source .env.beta && set +a && \
easy-manim-eval-run \
  --data-dir data \
  --suite evals/beta_prompt_suite.json \
  --include-tag real-provider \
  --include-tag quality \
  --match-all-tags \
  --json
```

Expected:
- `total_cases = 5`
- `completed = 5`
- `failed = 0`
- `quality.pass_rate = 1.0`
- `provider-mathtex-formula` no longer fails with `render_failed`

**Step 4: If the live formula case still fails, do one more targeted iteration**

Only if `provider-mathtex-formula` still fails:
- inspect the new `current_script.py` and `failure_context.json`
- add one more prompt instruction tied to the exact bad pattern that appeared
- rerun only after a focused unit test captures that new pattern

**Step 5: Commit**

```bash
git add docs/runbooks/real-provider-trial.md docs/runbooks/beta-ops.md
git commit -m "docs: capture formula animation regression workflow"
```

