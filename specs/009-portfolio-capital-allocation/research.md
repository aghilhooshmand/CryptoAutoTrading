# Research: Portfolio & Capital Allocation Core

**Feature**: `009-portfolio-capital-allocation`  
**Date**: 2026-08-14  
**Spec**: [spec.md](./spec.md)

## Decision 1: Persist portfolio in SQLite via thin `/portfolio` API

**Decision**: Store the local portfolio and allocations in the existing SQLite
database behind a FastAPI router under `/portfolio`. Frontend Portfolio page
consumes this API. Do **not** use `localStorage` as source of truth.

**Rationale**:
- Spec requires persist-after-restart, reject-leave-last-good, and hard capital
  invariants — same pattern as Feature 008 Settings.
- Constitution XV prefers SQLite for local persistence.
- Keeps capital authority on the backend (strategies cannot invent capital).

**Alternatives considered**:
- Frontend-only state — rejected: weak invariants, lost on refresh, drifts from
  future Simulation binding.
- Separate DB file — rejected: unnecessary second channel.

## Decision 2: Singleton portfolio + allocation rows

**Decision**:
- One `portfolio` singleton row (fixed `id=1`) for cash and portfolio-level
  P&L/deployed fields.
- Many `portfolio_allocations` rows keyed by UUID, FK to portfolio.

Overwrite cash via funding endpoints; mutate allocations via create/resize/
release. No append-only capital history table in v1.

**Rationale**: Spec entities are current Portfolio + Allocation records for
inspection/reproducibility of *effective* state, not a full ledger of every
tick.

**Alternatives considered**:
- Event-sourced ledger in 009 — deferred; later features can add journals.
- Soft-delete only — release may hard-delete or mark released; prefer
  hard-delete/release that frees reserved immediately for v1 simplicity.

## Decision 3: Capital identity `available = cash − reserved`

**Decision** (clarify Q3):
- `reserved` = sum of active allocation reserved sizes
- `available = cash − reserved`
- Enforce `reserved ≥ 0`, `available ≥ 0`, `reserved ≤ cash`
- `deployed` reported separately; **0** in Feature 009
- Positions list **empty** in Feature 009

**Rationale**: Matches “reserve without spending”; keeps deployed ready for
later binding without double-subtracting in v1.

**Alternatives considered**:
- Subtract deployed from available now — rejected while deployed stays unused.
- Equity mark-to-market formula — deferred until positions exist.

## Decision 4: Explicit Portfolio funding (not Settings / Simulation)

**Decision** (clarify Q1 / Q5):
- Operator sets initial cash via Portfolio funding action.
- Later increases/decreases use the same controlled funding path.
- Funding reduction with `new_cash < reserved` → **reject**; operator must
  release/resize allocations first.
- Feature 008 Settings and active Simulation session do **not** own or silently
  seed portfolio cash.

**Rationale**: Portfolio is the capital authority; Settings remain defaults only
(XXXIII); Simulation accounting stays session-local (FR-009).

**Alternatives considered**:
- Mirror Settings `startingCapital` — rejected (clarify).
- Mirror Simulation cash — rejected (would couple and rewrite narratives).

## Decision 5: Allocations are reservations with optional non-unique targets

**Decision** (clarify Q4):
- Required: stable allocation id, operator label, reserved size (> 0).
- Optional: `targetRef` (strategy id / program label string) — **not unique**.
- Create / resize / release only; no trading side effects.

**Rationale**: Spec future scenarios need flexible labeling; uniqueness would
falsely imply strategy ownership of capital.

**Alternatives considered**:
- Unique per strategy — rejected.
- Require registry strategy id — rejected for v1 (Torque/program labels later).

## Decision 6: Foundation-first; no Simulation/Backtest ledger migration

**Decision**: Do not rewrite session/run fill accounting onto the portfolio
ledger in 009. Keep regression suites green. Later features bind trading to
allocations.

**Rationale**: Spec FR-009 / assumptions; reduces blast radius.

**Alternatives considered**:
- Thin read-only Simulation mirror for deployed/positions — rejected (clarify Q2).

## Decision 7: Package and UI placement

**Decision**:
- Backend package: `backend/app/portfolio/` (mirror `app.settings`).
- UI: expand `PortfolioPage` under existing primary Portfolio nav.
- Inherit `docs/UI_UX_STANDARDS.md` (labels, units, help, validation, busy,
  confirm release).

**Rationale**: Constitution XIII (three primary areas); XIV UX principles.

**Alternatives considered**:
- Auto Trading tab for allocations — rejected; capital belongs in Portfolio.
