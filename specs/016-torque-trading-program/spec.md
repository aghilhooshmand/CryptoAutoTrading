# Feature Specification: Torque Trading Program Core

**Feature Branch**: `016-torque-trading-program`

**Created**: 2026-09-04

**Status**: PLANNED (do not implement before Feature **015** Controlled Real MVP-2)

**Input**: Compose existing CryptoAutoTrading strategies into searchable Torque
programs using the general **FORGE `torque`** package for program form
(`check`). This project owns strategy meaning, binding to Controller → Risk →
Execution, and Backtest evaluation. Minimum composition (AND / OR / vote)
absorbs Feature 018 direction. Prepares an evaluate surface for Feature 019
UGE. Clarifications from operator session 2026-09-04 (FORGE collaboration
pattern).

## Clarifications

### Session 2026-09-04

- Q: Own Torque language vs call FORGE? → A: **Call FORGE `torque`** for form /
  `check`. CryptoAutoTrading registers what strategy names mean (same pattern
  as FORCE registering ML leaves). Do not put trading logic into FORGE.
- Q: What are program leaves? → A: **Existing Feature 005/006 strategies**
  with parameters (e.g. RSI / MACD / Dual EMA periods). Motivation: humans
  cannot search all param × combination space; Torque spells candidates for
  later UGE.
- Q: What does combination mean (e.g. AVG)? → A: MVP uses **agreement-style**
  composition (**AND / OR / vote**): e.g. both strategies signal sell → sell.
  A name like `AVG` is allowed only when this feature defines exact signal
  semantics; do not assume arithmetic mean of series unless specified.
- Q: Realtime UGE while prices move? → A: **Out of 016.** Evaluation here is
  offline Backtest of a phenotype. Continuous live re-search is deferred
  (Feature 019+ later challenge).

## Behavior locks (non-negotiable)

1. **FORGE dependency** — Feature 016 MUST use FORGE `torque` for well-formed
   phenotype checking. MUST NOT fork a second Torque language.
2. **Same pipeline** — Phenotypes MUST produce trading intent into
   Controller → Risk → Execution → Accounting (constitution XXXV). No direct
   balance mutation or exchange order calls from Torque.
3. **Domain ownership** — Strategy catalogue, parameter bounds, composition
   semantics, and Backtest evaluation MUST live in this repo.
4. **No Real bypass** — Torque MUST NOT auto-enable Real trading or skip
   confirmation gates (Feature 015 / 024).
5. **Gate** — MUST NOT start implementation before Feature 015 Controlled Real
   MVP-2 is accepted (ROADMAP Phase D).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Check and bind a phenotype (Priority: P1)

As an operator/developer, I want a Torque phenotype string that names our
strategies and composition ops to be checked with FORGE `torque` and bound to
our registry so invalid programs fail closed before Backtest.

**Independent Test**: Valid phenotype passes `torque.check` and binds; unknown
leaf or bad params fails with a clear error; no Backtest run on invalid form.

### User Story 2 - Backtest a composed program (Priority: P1)

As an operator, I want AND/OR/vote (or equivalent) of two strategies with
chosen parameters to run through deterministic Backtest so I can see PnL with
fees/slippage.

**Independent Test**: Fixed candles + fixed phenotype → same metrics on replay;
intent still passes Controller/Risk.

### User Story 3 - Evaluate API for UGE (Priority: P2)

As Feature 019, I need `evaluate(phenotype, data/config) → metrics` so UGE can
score individuals without owning fitness.

**Independent Test**: Evaluate returns stable metric fields; secrets and live
keys not required for historical evaluation.

## Requirements

- **FR-001**: System MUST depend on FORGE `torque` and use `check` (or documented
  equivalent) for phenotype well-formedness.
- **FR-002**: System MUST register existing strategy leaves with parameter
  schemas/bounds usable by Torque programs and later BNF.
- **FR-003**: System MUST support searchable strategy parameters (e.g. period
  variants), not only fixed starter params.
- **FR-004**: System MUST implement MVP composition **AND / OR / vote** (or
  documented equivalents) with explicit buy/sell/hold agreement semantics.
- **FR-005**: Valid phenotypes MUST evaluate via Feature **004** Backtest (same
  engine semantics; no parallel backtest).
- **FR-006**: Torque MUST NOT bypass Controller or Risk.
- **FR-007**: System MUST expose an evaluate/fitness-ready interface for
  Feature 019 (metrics only; no UGE engine required in 016).
- **FR-008**: Invalid phenotype MUST fail closed (no invented fills).

## Success Criteria

- **SC-001**: At least two existing strategies can appear as leaves with
  parameters in a checked phenotype.
- **SC-002**: At least one composition op (AND or vote) changes outcomes vs a
  single leaf on a fixed fixture in a documented way.
- **SC-003**: Replay of the same phenotype + candles yields identical Backtest
  metrics.
- **SC-004**: No FORGE package contains CryptoAutoTrading strategy or exchange
  code.

## Out of scope

- Implementing FORGE Torque itself
- UGE search loop (019)
- Torque-owned capital allocation (017)
- Realtime continuous evolution
- Autonomous Real from phenotypes (024)
- New indicator engine unrelated to existing strategy registry (unless later
  amendment)

## Assumptions

- FORGE `torque` is installable (path/editable/published) when 016 starts.
- Feature 015 MVP-2 is done before coding 016.
- Existing strategies remain the first leaf catalogue.
