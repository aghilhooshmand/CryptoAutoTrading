# Research: Advanced Risk Management

**Feature**: `010-advanced-risk-management`  
**Date**: 2026-08-14  
**Spec**: [spec.md](./spec.md)

## Decision 1: One shared RiskManager (no second engine)

**Decision**: Extend `app.simulation.control.risk.RiskManager` and `RiskContext`.
Add optional portfolio-context fields. Backtest/Comparison call the same
class with portfolio context disabled (`None` / flag off).

**Rationale**: Constitution III and FR-001 forbid a PortfolioRisk /
BacktestRisk fork. Feature 004 already imports Simulation Risk.

**Alternatives considered**:
- Separate `app.risk` package with two adapters — deferred (unnecessary for MVP).
- Duplicate portfolio checks only in `session_service` — rejected (bypasses
  Risk authority and journals).

## Decision 2: Shared reason catalog (code ≠ message)

**Decision**: New module `app.simulation.control.reasons` (or equivalent) maps
stable `reason_code` strings to default human-readable messages. Journals store
both. Risk returns first failing code under fixed precedence (clarify lock).
Existing Feature 003/004 codes keep meanings; new portfolio codes are additive.

**Rationale**: Traceability (VII) and Torque/real-money reuse need stable codes;
UI copy can evolve without renaming codes.

**Alternatives considered**:
- Enum-only without messages — rejected (operators need readable journals).
- Return all failing reasons — rejected (clarify chose first-fail only).

## Decision 3: Portfolio capital gates (clarify D)

**Decision**:
- **Create/start**: reject if `allocated_capital > portfolio.available`
  (`available = quote_cash − reserved`). Never use `available − deployed`.
- **BUY unbound**: do **not** re-check `available`; session cash / allocated /
  max_position remain.
- **BUY bound**: intended notional must fit
  `allocation.reservedSize − binding_deployed` where binding deployed is the
  session’s open long USDT `cost_basis` (Feature 009 projection for that
  session).

**Rationale**: Matches clarify answers; preserves Feature 009 reservation
identity; makes sleeves real only when bound.

**Alternatives considered**:
- Re-check available on every BUY — rejected (operator chose D).
- Subtract deployed from available — rejected (double-count vs 009).

## Decision 4: Allocation resize/release while bound

**Decision**: While any Simulation is bound to allocation A:
- `DELETE` / release A → `400` with catalog code.
- Resize A → accept only if `newReserved >= current_deployed` for that binding;
  else reject, prior state unchanged.

**Rationale**: Fail-closed; avoids over-deployed limbo (clarify D).

**Alternatives considered**: Allow over-deploy with warning — rejected.

## Decision 5: Portfolio max-loss freeze

**Decision**: At Simulation start, persist:
- `portfolioLossBaselineKind`: `equity` | `quote_cash`
- `portfolioLossBaselineValue`: decimal string
- Optional bound: absolute amount and/or rate → derived amount

Kind = `equity` if `equityComplete` else `quote_cash`.  
Loss = `baseline − current` under frozen kind.  
If current uncomputable → reject BUYs; do **not** invent portfolio-loss stop.  
When computable and loss ≥ bound → stop with `portfolio_max_loss` (forced
flatten per Feature 003).

**Rationale**: Clarify A; constitution VIII.

**Alternatives considered**: Always USDT-only; recompute baseline — rejected.

## Decision 6: Optional per-symbol weight

**Decision**: Optional max weight W. On BUY, project post-BUY known-value of
the non-quote asset and known-value equity; reject if weight > W. Stale per
Feature 002. Missing/incomplete → reject increasing exposure. USDT uncapped.

**Rationale**: Clarify A; P2 guardrail without full policy product.

**Alternatives considered**: Skip check when incomplete — rejected (fail open).

## Decision 7: Settings defaults only

**Decision**: Add optional Settings fields for portfolio max-loss (amount
and/or rate), per-symbol max weight, and optionally preferred allocation id
for form prefill. Copy into Simulation effective config at create. Never rewrite
historical sessions.

**Rationale**: Constitution XXXIII / Feature 008 pattern.

## Decision 8: Backtest / Comparison

**Decision**: No live Portfolio gates. Same `RiskManager`; portfolio fields
unset/disabled. Session optional profit/loss/max trades unchanged (Feature 004).

**Rationale**: Spec FR-007 / FR-012; one authority without fake Portfolio books
on historical runs.

## Decision 9: Intended notional for Risk portfolio checks

**Decision**: For bound allocation remaining and per-symbol projection, Risk
uses the same intended-notional sizing inputs as Execution would
(`min(affordable, allocated, max_position)` conceptually) so Risk does not
approve a size Execution cannot place. Execution remains fail-closed for dust /
insufficient session cash.

**Rationale**: FR-009; avoid approve-then-fail surprises where avoidable.

## Resolved NEEDS CLARIFICATION

All clarify-session decisions are locked in `spec.md`. No open
NEEDS CLARIFICATION items remain for planning.
