# Kimi Code Frontend Handoff Round 3 2026-04-06

## Goal

Apply a narrow frontend cleanup pass based on the latest re-audit.

This is not a redesign task and not a repo-wide refactor.

Work only inside `ui/`.

## Hard Constraints

- Do not touch backend files.
- Do not rewrite unrelated pages.
- Do not reformat the whole project.
- Prefer small, local fixes with clear intent.
- Keep existing behavior unless it conflicts with accessibility or maintainability.

## Remaining Issues To Fix

### 1. Reduced-motion bug in AuthModal

Problem:

- `src/components/AuthModal/AuthModal.module.css` gives the collapsed auth entry a continuous pulse animation.
- The reduced-motion media query disables old class names, but it does not disable the current collapsed trigger animation.

Required outcome:

- In `prefers-reduced-motion: reduce`, the collapsed auth trigger should not keep pulsing.
- Check the live class names used by `AuthModal.tsx` and make the media query match them.

Primary files:

- `src/components/AuthModal/AuthModal.module.css`
- `src/components/AuthModal/AuthModal.tsx`

### 2. Touch-target minimums in shared controls

Problem:

- Shared button styles still allow `32px` / `36px` sizes.
- Shared icon button styles still allow `32px` / `36px` sizes.
- Some custom checkbox UI in the profile page is only `22px`.

Required outcome:

- Shared interactive controls used as primary/tappable controls should not ship below `44x44`.
- If very small visual styles must remain, preserve visual size while increasing the actual hit area.
- Fix the profile custom checkbox so pointer and touch interaction are comfortably tappable.

Primary files:

- `src/components/Button/Button.module.css`
- `src/features/profile/ProfilePageV2.css`
- `src/features/profile/ProfilePageV2.tsx`

### 3. Theme/token inconsistency in active background components

Problem:

- Active background/decorative components still use hard-coded gradient hex values and bypass the token system.
- This makes theme direction harder to maintain and weakens theme switching consistency.

Required outcome:

- Replace hard-coded colors in active background/decorative components with existing semantic tokens where practical.
- Keep the current overall soft/kawaii direction.
- Do not switch the app to the unused dark-glass direction.

Primary files:

- `src/components/GradientBackground.tsx`
- `src/components/KawaiiDecorations.tsx`
- related CSS files only if needed

### 4. Dead-theme maintenance trap

Problem:

- `src/styles/theme-v2.css` is not imported by the app entry, but it still has a dedicated test.
- This creates maintenance noise and encourages future changes in an unused theme path.

Required outcome:

- Decide one of these small-scope fixes:
  - either remove the obsolete test if `theme-v2.css` is intentionally unused,
  - or add a short clarifying comment/doc note near the test or file so future maintainers know it is legacy/non-runtime.
- Do not revive `theme-v2.css` as the active runtime theme.

Primary files:

- `src/styles/theme-v2.test.ts`
- `src/styles/theme-v2.css`
- `src/main.tsx`

## Verification Required

Run:

```bash
cd ui
npm run lint
npm run test -- --run
npm run build
```

## Output Format

Report back with:

1. files changed
2. which of the 4 issues were fully fixed
3. anything partially fixed or deferred
4. verification results
