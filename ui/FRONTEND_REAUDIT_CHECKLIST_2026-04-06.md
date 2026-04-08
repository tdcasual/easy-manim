# Frontend Re-Audit Checklist 2026-04-06

Use this after Kimi Code completes the frontend remediation pass.

## Gate Checks

- `cd ui && npm run lint`
- `cd ui && npm run test`
- `cd ui && npm run build`

Expected result:

- all three commands pass

## Accessibility

- keyboard navigation works across login, task pages, videos, profile, and studio
- visible `:focus-visible` state exists on all primary controls
- no critical control relies on `outline: none` without a real replacement
- dialog/drawer close behavior works with keyboard and pointer
- touch targets for close/search/utility buttons are at least `44x44`

## Responsive

- no obvious overflow at mobile widths
- login page remains usable on narrow screens
- history drawer and settings/help panels remain usable on small screens
- decorative layers do not crowd form controls or core content

## Theming

- token usage is more centralized
- hard-coded component colors are reduced
- visual direction is coherent rather than split between conflicting styles

## Interaction Quality

- modal/drawer patterns are consistent
- search/filter/input controls feel visually and behaviorally aligned
- decoration no longer outweighs information hierarchy

## Output For Re-Audit Summary

Report back with:

1. passed checks
2. remaining issues by severity
3. regressions introduced, if any
4. whether another cleanup pass is still needed
