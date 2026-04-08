# Kimi Code Frontend Handoff 2026-04-06

## Goal

Fix the frontend issues identified in the latest audit without changing backend behavior.

Primary reference:

- `ui/FRONTEND_AUDIT_2026-04-06.md`

Do not treat this as a redesign-from-scratch task. This is a targeted quality-improvement pass.

## Scope

Work only inside `ui/` unless a frontend build/test integration absolutely requires a tiny repo-level change.

Focus on:

1. lint and formatting hygiene
2. accessibility and focus behavior
3. dialog/drawer semantics
4. responsive safety
5. theme/token consistency
6. reducing decorative excess on task-heavy screens

Do not modify backend Python logic as part of this task.

## Execution Order

### Phase 1: Restore frontend quality gate

Run:

```bash
cd ui
npm run lint -- --fix
```

Then manually clean remaining warnings/errors.

Acceptance criteria:

- `npm run lint` passes
- formatting-only churn is separated from semantic fixes as much as practical

### Phase 2: Standardize focus-visible behavior

Audit and fix focus handling in:

- `src/styles/theme-v2.css`
- `src/components/Input/Input.module.css`
- `src/features/auth/LoginPage.css`
- `src/features/profile/ProfilePageV2.css`
- `src/features/tasks/TasksPageV2.css`
- `src/features/videos/VideosPageV2.css`
- any related shared control styles

Required outcome:

- remove inconsistent `outline: none` usage unless there is a clear accessible replacement
- use one shared `:focus-visible` approach
- keyboard focus must remain obvious on buttons, icon buttons, inputs, selects, textareas, chips, and search fields

### Phase 3: Refactor dialog/backdrop behavior

Target components:

- `src/components/AuthModal/AuthModal.tsx`
- `src/studio/components/HelpPanel.tsx`
- `src/studio/components/HistoryDrawer.tsx`
- `src/studio/components/SettingsPanel.tsx`

Required outcome:

- avoid repeating clickable bare overlay `div` patterns
- centralize overlay close behavior in a reusable dialog/drawer shell if practical
- keep ESC close and close-button behavior working
- preserve existing UX unless it conflicts with accessibility

### Phase 4: Fix responsive and touch-target issues

Priority files:

- `src/studio/styles/HistoryDrawer.module.css`
- `src/features/auth/LoginPage.css`
- `src/features/videos/VideosPageV2.css`
- related studio/settings/help panel styles

Required outcome:

- minimum hit area of common interactive controls should be at least `44x44`
- replace risky fixed sizes with `clamp()`, `minmax()`, or safer responsive rules
- no obvious viewport overflow on mobile-width layouts

### Phase 5: Normalize theme direction

Investigate:

- `src/styles/tokens.css`
- `src/styles/theme-v2.css`
- inline color values in React components such as `SettingsPanel.tsx`

Required outcome:

- pick one dominant visual direction and reduce internal contradictions
- remove component-level hard-coded colors where semantic tokens should be used
- do not leave both a pastel kawaii system and a cyan/purple dark-glass system fighting each other in the same surfaces

This phase should be evolutionary, not a large visual rewrite.

### Phase 6: Reduce decorative overhead

Trim non-functional:

- blur
- glow
- floating decoration
- ornamental emoji repetition
- heavy animated backgrounds on task-centric screens

Required outcome:

- task content and controls should dominate visual hierarchy
- decoration should support, not compete with, workflows

## Constraints

- Keep existing routes, data flow, and API contracts intact.
- Do not remove tests unless they are invalid and replaced with better coverage.
- Prefer shared primitives over page-level one-off fixes.
- Preserve behavior where possible; improve semantics and maintainability.

## Required Verification

Before handing back:

```bash
cd ui
npm run lint
npm run test
npm run build
```

If any command fails, document exactly what failed and why.

## Output Format Requested From Kimi Code

When done, report:

1. files changed
2. which audit items were fixed
3. anything intentionally deferred
4. verification command results

## Follow-Up Review

After Kimi Code finishes, a second audit should verify:

1. focus-visible is consistent
2. overlays/dialogs are semantically safer
3. mobile/touch issues are reduced
4. lint gate is healthy
5. theme direction is more coherent
6. decorative effects no longer overpower task surfaces
