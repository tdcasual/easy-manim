# Frontend Remediation Checklist

> **For Kimi Code / Frontend implementer:** follow this checklist in order, keep changes token-driven/i18n-driven, and avoid hardcoded copy, spacing branches, or one-off viewport hacks.

**Goal:** Resolve the current highest-impact frontend audit issues after the recent UI redesign, with emphasis on mobile usability, polling efficiency, and Studio first-screen clarity.

**Guardrails:**
- Reuse existing design tokens, Tailwind utilities, locale dictionaries, and shared UI primitives.
- Do not introduce hardcoded text in components; all new labels must come from locale files.
- Do not add page-specific magic numbers when an existing breakpoint hook, token, or helper can express the intent.
- Prefer configuration arrays/helpers over duplicated button markup.
- Preserve existing auth, history, help, and settings flows.

---

## P1: Compact the Studio mobile header

**Problem**
- On small screens the Studio header is visually crowded and action density is too high.

**Files**
- Modify: `ui/src/studio/Studio.tsx`
- Modify: `ui/src/locales/zh-CN.json`
- Modify: `ui/src/locales/en-US.json`
- Reuse: `ui/src/components/ui/sheet.tsx`
- Test: `ui/src/studio/Studio.mobile.test.tsx`

**Required outcome**
- Desktop keeps the current direct toolbar actions.
- Mobile collapses secondary actions into a single menu/sheet.
- Keep primary access to locale switching.
- Theme toggle can move into the mobile action sheet.
- Use one shared action-definition array instead of duplicating button implementations.

**Validation**
- Mobile test covers menu trigger and sheet actions.
- Existing Studio locale/history tests still pass.

## P1: Rebalance the Studio first screen

**Problem**
- The empty stage occupies too much visual weight on mobile and pushes the prompt too low.

**Files**
- Modify: `ui/src/studio/Studio.tsx`
- Modify: `ui/src/studio/components/VideoStage.tsx`
- Test: `ui/src/studio/components/VideoStage.test.tsx`

**Required outcome**
- Mobile stage uses a compact empty-state treatment.
- Composer area stays visually prioritized near the bottom of the viewport.
- Preserve the same copy and actions; change layout emphasis, not product behavior.

**Validation**
- Compact mode is testable from component output.
- Mobile screenshot shows header + stage + prompt without crowding.

## P1: Stop unnecessary task polling

**Problem**
- Tasks page keeps polling even when nothing is active, which adds background noise and unnecessary API load.

**Files**
- Modify: `ui/src/features/tasks/TasksPageV2.tsx`
- Test: `ui/src/features/tasks/TasksPageV2.test.tsx`

**Required outcome**
- Initial load still happens immediately.
- Periodic polling only runs when there are active tasks (`queued` / `running`) and the document is visible.
- Returning to a visible tab refreshes data once.
- Polling behavior is driven by shared constants/helpers, not inline status strings repeated across the component.

**Validation**
- Add failing tests first for “no active tasks => no repeat polling”.
- Add failing tests first for “active tasks => repeat polling while visible”.

## P2: Reduce style-system drift at the runtime entrypoint

**Problem**
- New and legacy style layers are still loaded together, increasing visual drift risk.

**Files**
- Modify: `ui/src/main.tsx`
- Optional follow-up: create a documented runtime style entrypoint if needed

**Required outcome**
- Document the current layering contract explicitly.
- If safe, narrow legacy imports to the surfaces that still need them instead of globally mounting every layer.
- Avoid breaking legacy pages during this pass; this is a controlled cleanup, not a blind delete.

**Validation**
- `npm run build`
- Smoke-check login, tasks, studio

## Definition of done

- `npm test` passes for touched areas.
- `npm run lint` has no new warnings/errors from this change.
- `npm run build` passes.
- Screenshots confirm mobile Studio is less crowded.
