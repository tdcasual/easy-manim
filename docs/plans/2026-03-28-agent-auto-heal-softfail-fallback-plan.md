# 2026-03-28 Agent Auto-Heal / Soft-Fail / Fallback Plan

## Goal

Reduce user-visible hard failures as much as possible. The practical target is not mathematical zero failure, but:

1. auto-repair common retryable failures
2. downgrade recoverable quality failures into deliverable outcomes when appropriate
3. provide a deterministic fallback render path before surfacing terminal failure

## Current confirmed state

- The workflow already calls `auto_repair_service.maybe_schedule_repair(task)` after failure.
- `FailureContract` already classifies provider/runtime/render/validation/preview issues.
- `near_blank_preview` and `static_previews` now exist in `DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES` locally.
- `auto_repair_enabled` is still opt-in via settings/env, not on by default in code.
- Task status model is still binary enough that many deliverable-but-imperfect outcomes end up as `failed`.

## Track A: Make auto-repair actually effective online

### A1. Deployment prerequisites

- Confirm deployed easy-manim environment includes:
  - `EASY_MANIM_AUTO_REPAIR_ENABLED=true`
  - reasonable `EASY_MANIM_AUTO_REPAIR_MAX_CHILDREN_PER_ROOT` (recommend `1` initially)
  - default or explicit retryable issue codes including:
    - `near_blank_preview`
    - `static_previews`
- Redeploy service so the latest code and env take effect.

### A2. Online verification checklist

1. Submit a minimal task known to trigger `near_blank_preview`.
2. Verify first task enters `failed` with preview-quality issue code.
3. Verify `auto_repair_decision.created=true` in events/snapshot.
4. Verify a child task is created with `attempt_kind=auto_repair`.
5. Verify child task either:
   - completes successfully, or
   - fails with a different issue code that informs next policy work.

### A3. Recommended near-term code improvements

- Expose auto-repair outcome more clearly in task/result APIs:
  - latest child task id
  - whether auto-repair was attempted
  - whether final completion came from repair lineage
- Add one integration test that simulates a retryable preview failure and confirms child repair creation.

## Track B: Introduce soft-fail outcomes

## Problem

Today the system tends to map many validation failures directly to `FAILED`, even when a video artifact exists and is potentially usable.

## Proposed minimal approach

Do not immediately add a new top-level DB task status. Instead, add a delivery/result layer first.

### B1. New result semantics

Add result metadata fields such as:

- `delivery_status`: `ready` | `ready_with_warnings` | `not_deliverable`
- `warning_codes`: list[str]
- `final_decision`: `pass` | `soft_pass` | `fail`

### B2. Soft-pass candidates

Initial candidates for `soft_pass`:

- `near_blank_preview` after repair budget exhausted but final video exists
- `static_previews` where video is still technically valid and viewable

### B3. Hard-fail only for truly blocking cases

Remain terminal for:

- provider auth errors
- runtime policy violations
- missing runtime dependencies with no downgrade path
- render failure with no output artifact
- corrupted/undeliverable output

## Track C: Fallback render strategy

## Goal

If generative attempts keep failing, produce a deterministic safe video rather than surfacing an empty failure when possible.

### C1. Trigger point

After normal attempt + allowed auto-repair attempts are exhausted, and only for approved failure classes.

### C2. Where to implement

Recommended location: workflow/application layer, after failed validation lineage is understood, not inside validators.

Potential structure:

- `FallbackRenderService`
- called from the auto-repair / failure handling path
- creates a final child task with a deterministic prompt/script template

### C3. First fallback template

Use a highly reliable minimal template:

- light background from frame 1
- immediate visible title text
- simple shape / underline / accent animation
- fixed 3-5 second duration
- no LaTeX
- no complex transforms
- conservative resolution and frame rate

### C4. Which failures should fallback

Fallback-eligible after repair exhaustion:

- `near_blank_preview`
- `static_previews`
- selected `render_failed` cases after targeted simplification

Not fallback-eligible:

- provider auth errors
- sandbox/runtime policy violations
- unsafe content/policy failures

## Suggested policy matrix

- `near_blank_preview` -> auto-repair -> fallback template -> soft-pass if artifact usable
- `static_previews` -> auto-repair -> fallback template -> soft-pass if artifact usable
- `render_failed` -> targeted repair -> simplified scene retry -> fallback template if safe
- `provider_timeout` / `provider_rate_limited` -> retry later with backoff, no fallback render yet
- `provider_auth_error` -> terminal + operator action
- `latex_dependency_missing` -> latex-free regeneration path
- `sandbox_policy_violation` -> terminal

## Recommended implementation order

1. Turn on and verify online auto-repair.
2. Add integration coverage for retryable preview failures.
3. Add result-layer `soft_pass` / `ready_with_warnings` metadata.
4. Add deterministic fallback template path for preview-quality failures.
5. Expand to selected render/runtime downgrade flows.

## Success criteria

- Common preview-quality failures no longer stop at first failed task.
- User can still receive a deliverable result when quality issues are non-blocking.
- Hard failures are reserved for genuinely unrecoverable cases.
- Operator can trace whether delivery came from normal generation, auto-repair, or fallback.
