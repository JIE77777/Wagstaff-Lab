# WebCraft Cooking Tools Atlas Ledger UI Refactor

## Goal
- Apply Atlas Ledger layout to Cooking Tools desktop while preserving existing features.
- Mobile uses a dedicated workbench/results tab layout with no page scroll.
- Keep existing routes and the static lab page until cleanup is approved.

## Scope
- Template: apps/webcraft/templates/cooking_tools.html
- Styles: apps/webcraft/static/css/cooking.css (tool page only)
- JS: apps/webcraft/static/js/pages/cooking.js (viewport vars + mobile tabs)
- i18n: conf/i18n_ui.json (new tab labels)
- No API or route changes.

## Decisions
- Desktop: three-panel ledger grid (ingredients left, console top-right, results+detail bottom-right).
- Detail view embedded in results panel as a fixed dual-column layout.
- Mobile: workbench/results tab switch; results auto-open after explore/simulate.
- Internal panel scrolling only; no page scroll.

## Tasks
1. Replace tool page layout with ledger grid while keeping required IDs.
2. Add tool-scoped ledger styles and mobile tab rules.
3. Wire mobile tabs + viewport sizing in cooking.js.
4. Update i18n strings and run `make i18n`.
5. Validate desktop + mobile behaviors and no-scroll workbench.

## Risks
- CSS bleed into cooking encyclopedia if selectors are not scoped.
- Missing i18n build if `make i18n` is skipped.
