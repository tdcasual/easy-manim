# Main Branch Drift Audit

Date: 2026-04-03

## Classification Summary

| File | Current purpose | Why it still exists after the merge | Recommended disposition |
| --- | --- | --- | --- |
| `src/video_agent/adapters/storage/sqlite_bootstrap.py` | Experiments with replaying all bootstrap migrations while only recording newly seen migration ids. | The runtime-closure merge did not include this separate bootstrap strategy change, so it remained as local drift in the root worktree. | Move to a separate follow-up change. It is outside the Week 1 and Week 2 scope and should not ride along with runtime hardening or comparison work. |
| `src/video_agent/application/workflow_engine.py` | Preserves the explicit failure path for `sandbox_policy_violation` and `runtime_policy_violation` while keeping the degraded/emergency delivery guard flow intact. | A stash-restore conflict left the reconciled version uncommitted after the thread-native runtime merge. | Keep and finish in place this week. It belongs to the Week 1 `workflow_engine.py` triage surface and should stay visible until the brief is complete. |
| `docs/plans/2026-03-30-agent-system-priority-roadmap.md` | Captures the earlier system roadmap for memory, collaboration access, and orchestration refactor. | The roadmap was drafted during the runtime migration period but not yet committed on `main` when the runtime branch landed. | Keep and finish in place during Week 2 governance alignment. It remains the source document that needs thread-native language updates. |
| `docs/plans/2026-04-03-next-two-weeks-stage-roadmap.md` | Defines the current stage framing and the Week 1 / Week 2 execution order. | It was authored immediately after the merge as a stabilization roadmap and intentionally remains local until the follow-up work is complete. | Keep and finish in place this week. This is intentional planning state, not accidental drift. |
| `docs/plans/2026-04-03-week-1-main-branch-stabilization-plan.md` | Task-by-task execution plan for Week 1 cleanup and triage. | It was created as the active execution checklist for the post-merge stabilization pass. | Keep and finish in place this week. This is intentional planning state, not accidental drift. |
| `docs/plans/2026-04-03-week-2-comparison-and-governance-plan.md` | Task-by-task execution plan for comparison, governance alignment, and extraction seam selection. | It was created alongside the roadmap and still awaits execution. | Keep and finish in place this week. This is intentional planning state, not accidental drift. |

## Decision Notes

- The only root-worktree edit that does not belong to the active two-week closure plan is `src/video_agent/adapters/storage/sqlite_bootstrap.py`.
- The `workflow_engine.py` change is intentionally retained because Week 1 needs to document and triage the exact delivery-resolution region that was left in a reconciled-but-uncommitted state.
- The untracked roadmap and execution plans are intentional working documents. They should remain present until the stabilization and comparison tracks are complete, then be reviewed for final check-in together.

## Immediate Action

1. Move `src/video_agent/adapters/storage/sqlite_bootstrap.py` out of the root worktree into a named follow-up stash so it no longer pollutes Week 1 / Week 2 execution.
2. Keep `src/video_agent/application/workflow_engine.py` and the planning docs in place while the remaining planned work is executed.
3. Re-check `git status -sb` after the stash so the remaining drift is small, explicit, and aligned with the active roadmap.
