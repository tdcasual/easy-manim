# Frontend Audit 2026-04-06

## Anti-Patterns Verdict

Fail.

The current frontend does not read as a single intentional product system. It mixes two conflicting visual directions:

- a pastel "kawaii" system in `src/styles/tokens.css`
- a cyan/purple dark glass system in `src/styles/theme-v2.css`

It also shows several common AI-slop tells from the design guidelines:

- decorative glassmorphism used pervasively
- cyan-on-dark and purple-to-blue accent patterns
- decorative gradients and glow-heavy components
- modal-first interactions for secondary tasks
- repeated emoji decoration in labels, headers, and empty states

This does not mean the UI is unusable, but it does mean the frontend currently feels inconsistent, harder to maintain, and harder to evolve without regressions.

## Executive Summary

- Build: passed
- Test: passed (`37` files, `118` tests)
- Lint: failed with `283 problems (213 errors, 70 warnings)`
- Overall frontend score: `6/10`

Top issues:

1. The lint gate is not healthy, so frontend quality is no longer enforceable.
2. Focus visibility is suppressed in many custom inputs and form controls.
3. Dialog overlays are implemented as clickable `div`s instead of semantic interactive elements.
4. The design system is split between incompatible theme directions and hard-coded values.
5. Responsive behavior exists, but several layouts still rely on fixed dimensions and desktop-first decoration.

## Detailed Findings

### High

#### 1. Lint gate is broken

- Severity: High
- Category: Engineering hygiene / Frontend maintainability
- Evidence:
  - `npm run build` passed
  - `npm run test` passed
  - `npm run lint` failed with `283 problems (213 errors, 70 warnings)`
- Representative files:
  - `src/app/App.test.tsx`
  - `src/features/profile/ProfilePageV2.tsx`
  - `src/features/tasks/TaskDetailPageV2.tsx`
  - `src/lib/tasksApi.ts`
  - `src/lib/videoThreadsApi.ts`
- Impact:
  - Formatting noise hides real regressions.
  - Warnings such as `prefer-nullish-coalescing` are already widespread enough to be ignored.
  - Future reviews will have low signal and teams will stop trusting CI output.
- Recommendation:
  - Run `eslint --fix` first.
  - Separate mechanical formatting fixes from semantic fixes.
  - Then clean remaining `prefer-nullish-coalescing` warnings in feature batches.

#### 2. Focus visibility is inconsistently removed on key controls

- Severity: High
- Category: Accessibility
- WCAG: 2.4.7 Focus Visible
- Evidence:
  - `src/styles/theme-v2.css:308`
  - `src/components/Input/Input.module.css:139`
  - `src/components/Input/Input.module.css:190`
  - `src/features/auth/LoginPage.css:330`
  - `src/features/profile/ProfilePageV2.css:569`
  - `src/features/profile/ProfilePageV2.css:661`
  - `src/features/tasks/TasksPageV2.css:234`
  - `src/features/videos/VideosPageV2.css:221`
- Description:
  - Many custom controls set `outline: none`.
  - Some wrappers add replacement styling on `:focus` or `:focus-within`, but this is not consistently standardized and makes keyboard focus behavior harder to verify.
- Impact:
  - Keyboard users may lose clear focus indication.
  - The UI relies on visual subtleties like glow and border shifts, which are weaker than a consistent focus-visible system.
- Recommendation:
  - Standardize on a shared `:focus-visible` tokenized ring.
  - Remove local `outline: none` rules unless paired with an explicit accessible replacement.
  - Test tab navigation through login, filters, settings, profile forms, and studio input flows.

### Medium

#### 3. Dialog backdrops use clickable `div` overlays

- Severity: Medium
- Category: Accessibility / Semantics
- Evidence:
  - `src/components/AuthModal/AuthModal.tsx:128`
  - `src/studio/components/HelpPanel.tsx:43`
  - `src/studio/components/HistoryDrawer.tsx:74`
  - `src/studio/components/SettingsPanel.tsx:117`
- Description:
  - Dialog close-on-backdrop is implemented with bare `div` elements that respond to pointer clicks.
  - The dialogs do have close buttons and `useDialogA11y`, which is good, but the backdrop interaction itself is still non-semantic.
- Impact:
  - Pointer interaction exists without an equivalent semantic interactive surface.
  - This pattern is easy to copy into other components and gradually weakens a11y quality.
- Recommendation:
  - Keep the close button and ESC behavior.
  - Refactor overlay behavior into a reusable dialog shell with a semantic backdrop strategy and consistent event handling.

#### 4. Theme system is internally inconsistent

- Severity: Medium
- Category: Theming / Design system
- Evidence:
  - `src/styles/tokens.css`
  - `src/styles/theme-v2.css`
  - `src/studio/components/SettingsPanel.tsx:48`
- Description:
  - `tokens.css` defines a pastel kawaii system.
  - `theme-v2.css` defines a dark cyan/purple glass system with `Inter` and aurora styling.
  - `SettingsPanel.tsx` adds inline hard-coded hex colors on top of both systems.
- Impact:
  - Design decisions are no longer centralized.
  - Theme changes become expensive because values are distributed across CSS tokens, page styles, and inline component code.
  - The product feels visually fragmented.
- Recommendation:
  - Choose one primary visual system.
  - Move inline colors into semantic tokens.
  - Reserve special surfaces and effects for a small set of intentional moments.

#### 5. Fixed dimensions still create responsive risk

- Severity: Medium
- Category: Responsive design
- Evidence:
  - `src/studio/styles/HistoryDrawer.module.css:25` uses `width: 400px`
  - `src/features/auth/LoginPage.css:114` uses `grid-template-columns: 1fr 480px`
  - `src/features/auth/LoginPage.css:200`
  - `src/features/auth/LoginPage.css:201`
- Description:
  - There are mobile breakpoints, which is positive.
  - However, some layouts still depend on fixed desktop dimensions and large decorative surfaces, especially in the login experience and studio drawer.
- Impact:
  - The UI is more brittle under localization, zoom, or unusual viewport sizes.
  - Decorative layers can dominate on mid-size screens even when they do not fully break layout.
- Recommendation:
  - Replace fixed widths with `minmax()`, `clamp()`, and container-driven sizing where possible.
  - Reduce decorative element footprints before shrinking content.

#### 6. Several touch targets are below the recommended 44x44 size

- Severity: Medium
- Category: Accessibility / Mobile usability
- Evidence:
  - `src/features/videos/VideosPageV2.css:226`
  - `src/studio/styles/HistoryDrawer.module.css:80`
- Description:
  - The search clear control is `24x24`.
  - The history drawer close button is `40x40`.
- Impact:
  - Small touch targets increase mobile mis-taps and reduce accessibility.
- Recommendation:
  - Standardize compact interactive hit areas to at least `44x44`.
  - Preserve visual size if needed, but increase tappable area.

#### 7. Blur, glow, and decorative motion are overused

- Severity: Medium
- Category: Performance / Visual clarity
- Evidence:
  - `src/styles/theme-v2.css`
  - `src/styles/tokens.css`
  - `src/studio/styles/HistoryDrawer.module.css`
  - `src/features/auth/LoginPage.css`
- Description:
  - The frontend leans heavily on `backdrop-filter`, glow shadows, large animated backgrounds, decorative particles, floating elements, and emoji ornamentation.
- Impact:
  - Important content competes with decoration.
  - Lower-powered devices may pay a rendering cost for effects that do not improve task completion.
- Recommendation:
  - Treat blur and animated decoration as accent tools, not default styling primitives.
  - Audit each effect for purpose: hierarchy, feedback, or brand.

## Patterns & Systemic Issues

- `outline: none` appears across shared theme files, component CSS modules, and page-level styles.
- Multiple dialogs reimplement the same backdrop-close pattern.
- Visual tokens are not the single source of truth; CSS variables, hard-coded hex values, and inline styles coexist.
- Many components optimize for visual flourish before semantics and interaction robustness.
- Breakpoints exist, but sizing strategy is still largely fixed-width rather than fluid-first.

## Positive Findings

- The frontend is not fundamentally broken: build and tests both pass.
- A shared `useDialogA11y` hook already exists and is used in several dialogs.
- `src/styles/tokens.css` already includes hooks for reduced motion and high-contrast handling.
- Some responsive fallback work already exists in `LoginPage.css` and `HistoryDrawer.module.css`, so this is a refinement task, not a restart.

## Recommendations By Priority

### Immediate

1. Restore a healthy lint gate.
2. Standardize focus-visible behavior across all custom inputs, selects, textareas, and search fields.
3. Fix undersized touch targets in common controls.

### Short-Term

1. Refactor dialog overlays into one reusable accessible dialog container.
2. Remove hard-coded colors from React components and map them to design tokens.
3. Replace the highest-risk fixed sizes with fluid sizing primitives.

### Medium-Term

1. Pick one visual direction and delete the conflicting theme path.
2. Reduce decorative blur, glow, and motion on task-heavy screens.
3. Audit page-level CSS for repeated emoji/decorative content that weakens information hierarchy.

### Long-Term

1. Consolidate shared interaction styles into one form-control foundation.
2. Add Playwright or visual-regression checks for keyboard focus and small-screen layouts.
3. Add a frontend review checklist to PRs: focus-visible, touch target size, token usage, responsive behavior.

## Kimi Code Fix Backlog

Use this as the implementation list for Kimi Code.

1. Run frontend mechanical cleanup:
   - `cd ui && npm run lint -- --fix`
   - commit pure formatting fixes separately
   - then resolve remaining semantic lint warnings
2. Build a shared focus ring standard:
   - replace local `outline: none` patterns
   - enforce `:focus-visible` styling for inputs, selects, textareas, buttons, and icon buttons
3. Refactor modal/drawer shell:
   - create one reusable dialog/backdrop wrapper
   - migrate `AuthModal`, `HelpPanel`, `HistoryDrawer`, `SettingsPanel`
4. Normalize theming:
   - choose either the kawaii pastel system or the dark aurora glass system
   - remove mixed token sources and inline colors
5. Make common controls mobile-safe:
   - raise all tappable controls to at least `44x44`
   - start with search clear buttons, close buttons, and studio quick actions
6. Remove desktop-first fixed sizing where unnecessary:
   - review login page, history drawer, and studio side panels
   - replace fixed widths/heights with `clamp()` or `minmax()`
7. Trim decorative overhead:
   - reduce non-functional blur, glow, and animated ornaments on task-critical screens

## Suggested Commands / Skills For Follow-Up

- Use `normalize` for token and design-system consolidation.
- Use `harden` for focus states, semantics, and edge-case interaction fixes.
- Use `adapt` for responsive and touch-target improvements.
- Use `optimize` for blur, animation, and rendering cleanup.
- Use `polish` after the structural fixes land.
