# Feature Specification: UGE Grammatical Evolution Search

**Feature Branch**: `019-uge-grammatical-evolution`

**Created**: 2026-09-04

**Status**: PLANNED (do not implement before Feature **016** Torque MVP)

**Input**: Use the general **FORGE `uge`** Grammatical Evolution engine to
search a large space of Torque trading programs (strategy choice × parameters
× composition). CryptoAutoTrading owns the BNF, constraints, and fitness;
FORGE UGE owns search operators. Evaluation is **offline/batch** via Feature
004 Backtest through the Feature 016 evaluate bridge. Clarifications from
operator session 2026-09-04.

## Clarifications

### Session 2026-09-04

- Q: Build our own GE vs call FORGE UGE? → A: **Call FORGE `uge`**. Same
  generality as using UGE with FORCE for ML combinations — here the “leaves”
  are trading strategies, not sklearn models.
- Q: Why search? → A: Operators cannot manually try all RSI(9,21) vs
  RSI(10,22) and all combinations with MACD/etc. UGE proposes phenotypes;
  Backtest scores them.
- Q: Live prices while UGE runs for hours? → A: **Acknowledge and defer.**
  First milestone is offline historical search. Applying a **frozen** best
  phenotype later for signals is allowed after search works. Continuous
  re-search during live markets is **out of MVP**.
- Q: Where does fitness live? → A: **This project** (e.g. net profit vs buy &
  hold, later Sharpe/drawdown). UGE does not own crypto metrics.

## Behavior locks (non-negotiable)

1. **FORGE `uge`** is the search engine; MUST NOT reimplement a parallel GE
   core in this repo.
2. **BNF + fitness** MUST be owned by CryptoAutoTrading.
3. Every individual MUST be evaluated through Feature **016** binding +
   Feature **004** Backtest (Controller/Risk intact). No bypass pipeline.
4. **Offline/batch first** — MUST NOT require realtime UGE completion for
   Feature 019 DONE.
5. **Leakage** — MUST NOT select individuals using final holdout/test
   performance (constitution XXXVIII); minimum chronological train/val/test
   (Feature 021 min) accompanies first UGE.
6. Evolved phenotypes MUST NOT auto-enable Real or autonomous trading (024).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Offline UGE run (Priority: P1)

As an operator/researcher, I want to run UGE on a fixed candle snapshot and
grammar so I receive a best phenotype string and fitness that I can Backtest
reproducibly.

**Independent Test**: Same seed + data + grammar → same best phenotype (or
documented stochastic envelope); fitness matches standalone evaluate of that
phenotype.

### User Story 2 - Search parameters and combinations (Priority: P1)

As an operator, I want the grammar to include at least two strategies, parameter
ranges, and one composition op so search can discover combinations I would not
try by hand.

**Independent Test**: Grammar generates varied phenotypes; invalid ones are
rejected before or during evaluate without crashing the run.

### User Story 3 - Frozen phenotype after search (Priority: P2)

As an operator, I want to take the best phenotype from an offline run and
Backtest or (later) use it as a fixed rule set, without UGE still running.

**Independent Test**: Persisted phenotype string re-evaluates without UGE
process.

## Requirements

- **FR-001**: System MUST depend on FORGE `uge` (`UGEEngine` or documented
  equivalent).
- **FR-002**: System MUST supply a BNF/grammar over Feature 016 leaves and
  MVP composition ops with explicit constraints (max depth, param ranges).
- **FR-003**: Phenotype evaluation MUST call Feature 016 evaluate → Backtest;
  MUST use `torque.check` before scoring when required by 016.
- **FR-004**: Fitness MUST be explicit, cost-aware (fees/slippage), and
  returned in the form UGE expects (`EvaluationResult` / `Fitness` or
  documented adapter).
- **FR-005**: Initial fitness MAY be
  `program_net_profit - buy_and_hold_net_profit`; refinements documented in
  plan/tasks.
- **FR-006**: Runs MUST be reproducible from seed, grammar, data snapshot, and
  config.
- **FR-007**: Minimum chronological train/validation/(test) split MUST
  accompany first UGE (021 min).
- **FR-008**: Feature 019 MUST NOT place Real orders or start continuous live
  re-evolution.

## Success Criteria

- **SC-001**: One offline UGE experiment completes and returns a phenotype
  string Feature 016 can Backtest.
- **SC-002**: Fitness for that phenotype matches independent evaluate within
  documented tolerance (prefer exact on fixed fixtures).
- **SC-003**: Replay with same seed/config/data reproduces the experiment
  outcome.
- **SC-004**: No crypto/exchange code is added inside FORGE `uge`.

## Out of scope

- Rich experiment UI/persistence (020 — minimal logs OK)
- Advanced multi-objective fitness (022)
- Regime-aware programs (023)
- Realtime continuous UGE during live markets
- Autonomous Real trading (024)
- Torque capital allocation search (017)

## Assumptions

- Feature 016 evaluate bridge exists and is deterministic.
- FORGE `uge` is installable when 019 starts.
- First data is recorded/historical candles (Feature 002 venue), not live
  private fills.
