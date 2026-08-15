# UI / UX Standards

**Purpose**: Project-wide operator UI defaults so future features do not
restate basic form, feedback, and responsive rules.

**Authority**:

| Layer | Owns |
|-------|------|
| `.specify/memory/constitution.md` (XIV) | Permanent UI principles |
| This document | Normal UI defaults |
| Feature `spec.md` | Feature-specific UI only, or intentional exceptions |
| `docs/DEVELOPMENT_WORKFLOW.md` | DONE gate |

Keep this document short. It is not a design system.

---

## Forms

- Every input has a visible label.
- Show units explicitly (USDT, %, rate fraction vs percent points, seconds).
- Mark optional fields as optional.
- Prefer useful defaults; do not invent required values the operator must own.
- Put validation close to the affected field (or clearly associated with it).
- Add short help for technical or trading fields that are not obvious.
- Do not silently overwrite an in-progress draft when defaults or Settings change.

## Actions

- Use clear action names (`Run Backtest`, `Save`, `Create & start`) — not generic `Submit`.
- Show a loading / busy state for operations that take noticeable time.
- Prevent accidental double submission (disable while busy, or equivalent).
- Show visible feedback after meaningful success or failure.
- Confirm before destructive or important irreversible actions.

Do **not** require a toast after every click. Feedback only when it helps.

## Results

- Prefer human-readable numbers and percentages.
- Group important metrics so the operator can scan outcomes quickly.
- Prefer operator-facing labels over raw internal identifiers when both exist.

## Responsive UX

- Primary workflows must work around **375px** width.
- Forms stack on small screens; avoid horizontal-only layouts for required steps.
- No required interaction may depend on hover alone (use click/tap/focus).

## Consistency

Reuse shared patterns already in the frontend when they fit:

- Field help: `features/shared/InfoTooltip.tsx` (touch / click / focus)
- Inline hints: `.field-hint`
- Validation / alerts: `.form-error` with `role="alert"`
- Status / success: `.form-status`, `.form-warning`
- Money ↔ percent costs: `features/shared/CostRateFields.tsx`
- Busy buttons: disable + label change (`Saving…`, `Running…`)
- Confirmations: explicit confirm before Reset / delete / irreversible actions
- Mode badges: e.g. Simulation badge patterns — keep mode state obvious

Do not invent a parallel control just because copy differs slightly.

## Trading safety

- Simulation, Backtest, and Real Money states must be obvious in the UI.
- Important risk warnings must stay visible (not buried in hover text alone).
- Real-money actions need stronger treatment than ordinary navigation.

## Accessibility basics

- Keyboard / focus support where practical.
- Adequate touch targets for primary controls.
- Accessible names for icon-only controls.
- Do not communicate critical state with color alone.

---

## UI Done checklist

Before marking a user-facing feature DONE:

```text
[ ] Labels and units are clear; optionals marked
[ ] Non-obvious fields have short help (not hover-only)
[ ] Validation is visible and associated with the problem
[ ] Busy / success / failure feedback exists where meaningful
[ ] Destructive actions confirm; double-submit prevented where relevant
[ ] Important modes (Simulation / Real Money / etc.) are obvious
[ ] Primary flow usable around 375px
[ ] Reused existing shared UI patterns (no needless one-offs)
[ ] Spec notes only feature-specific UX or exceptions — not a copy of this doc
```
