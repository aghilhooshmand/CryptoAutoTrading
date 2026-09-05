# Feature Specification: UGE Grammatical Evolution Search

**Feature Branch**: `019-uge-grammatical-evolution`

**Created**: 2026-09-04

**Status**: **DONE** (2026-09-05) — offline UGE + freeze to Backtest UI;
Feature **015** Controlled Real may resume after operator review of sim/search MVP.


**Input**: Use the general **FORGE `uge`** Grammatical Evolution engine to
search a large space of Torque trading programs (strategy choice × parameters
× composition). CryptoAutoTrading owns the BNF, constraints, and fitness;
FORGE UGE owns search operators. Evaluation is **offline/batch** via Feature
004 Backtest (and optionally Simulation) through the Feature 016 evaluate
bridge. Operator lock 2026-09-04: prove useful combinations in sim before Real.

## Clarifications

### Session 2026-09-05

- Q: For the first UGE milestone, must fitness be exactly program net profit
  minus buy-and-hold, or may the operator change it? → A: **Option B** —
  default is `netProfit − buyAndHoldNetProfit` (maximise); operator MAY select
  a different **single** scalar via config from a documented allow-list.
  Multi-objective search remains Feature 022.
- Q: While UGE is searching, which candle split decides the winner? → A:
  **Option A** — evolution and best-individual selection use **train** fitness
  only; validation is reported after the run; test is holdout until a phenotype
  is frozen (never used for selection during search).
- Q: How should MVP grammar offer strategy parameters (e.g. RSI period)? → A:
  **Option A** — discrete alternatives in the BNF/grammar file (editable list);
  continuous min–max ranges deferred (too large a search space for MVP GE).
- Q: After UGE finds a best phenotype, what must MVP deliver for freeze/reuse?
  → A: **Option B** — persist the phenotype and make it **selectable in the
  Backtest UI** so the operator can run it like (and compare alongside) standard
  strategies. Simulation / Real use remains later roadmap work; 019 MUST NOT
  auto-enable Simulation or Real from a search result.
- Q: For 019 DONE, is Backtest UI enough to compare with Dual EMA/RSI, or must
  Strategy Comparison multi-run be wired too? → A: **Option A** — Backtest UI
  selection is enough for 019 DONE; Strategy Comparison multi-run deferred.

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
- Q: Where does fitness live? → A: **This project** (default net profit vs buy &
  hold; operator may switch to another single scalar via config — see Session
  2026-09-05). UGE does not own crypto metrics. Multi-objective later (022).
- Q: Real money before search? → A: **No.** Prove UGE on historical/sim
  evaluation first; Controlled Real (015) after a useful sim/search MVP.

## Behavior locks (non-negotiable)

1. **FORGE `uge`** is the search engine via install/import; MUST NOT reimplement
   a parallel GE core in this repo. MUST NOT copy, vendor, or paste FORGE/UGE
   source into this repository.
2. **BNF + fitness** MUST be owned by CryptoAutoTrading.
3. Every individual MUST be evaluated through Feature **016** binding +
   Feature **004** Backtest (Controller/Risk intact). Optional Simulation
   path MUST NOT bypass Risk. No RealExecutionAdapter in 019.
4. **Offline/batch first** — MUST NOT require realtime UGE completion for
   Feature 019 DONE.
5. **Leakage** — MUST NOT select individuals using validation or final
   holdout/test performance during search (constitution XXXVIII). Minimum
   chronological train/validation/test (Feature 021 min) accompanies first UGE:
   **train** for evolution/selection; **validation** for post-run reporting;
   **test** held out until a phenotype is frozen.
6. Evolved phenotypes MUST NOT auto-enable Real or autonomous trading (015/024).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Offline UGE run (Priority: P1)

As an operator/researcher, I want to run UGE on a fixed candle snapshot and
grammar so I receive a best phenotype string and fitness that I can Backtest
reproducibly.

**Independent Test**: Same seed + data + grammar → same best phenotype (or
documented stochastic envelope); fitness matches standalone evaluate of that
phenotype.

### User Story 2 - Search parameters and combinations (Priority: P1)

As an operator, I want the grammar to include at least two strategies,
**discrete** parameter choices, and one composition op so search can discover
combinations I would not try by hand (I can edit the grammar list to widen
choices later).

**Independent Test**: Grammar generates varied phenotypes; invalid ones are
rejected before or during evaluate without crashing the run.

### User Story 3 - Frozen phenotype after search (Priority: P2)

As an operator, I want to take the best phenotype from an offline run, persist
it, and **select it in the Backtest UI** so I can evaluate it like other
strategies (and compare results with Dual EMA / RSI / etc.), without UGE still
running. Applying the same frozen rule later in Simulation or Real is a
**later** step (015+); search MUST NOT auto-start those modes.

**Independent Test**: Persisted phenotype appears as a selectable Backtest
input; re-runs without a live UGE process; metrics match Feature 016 evaluate
of that phenotype string on the same candles/config.

## Requirements

- **FR-001**: System MUST depend on FORGE `uge` (`UGEEngine` or documented
  equivalent).
- **FR-002**: System MUST supply a BNF/grammar over Feature 016 leaves and
  MVP composition ops with explicit constraints (max depth; **discrete**
  parameter alternatives in the grammar — operator-editable). Continuous
  min–max parameter generation is out of 019 MVP.
- **FR-003**: Phenotype evaluation MUST call Feature 016 evaluate → Backtest;
  MUST use `torque.check` before scoring when required by 016.
- **FR-004**: Fitness MUST be explicit, cost-aware (fees/slippage), and
  returned in the form UGE expects (`EvaluationResult` / `Fitness` or
  documented adapter).
- **FR-005**: Default fitness MUST be
  `program_net_profit - buy_and_hold_net_profit` (maximise, cost-aware via
  Backtest fees/slippage). The operator MAY select an alternate **single**
  scalar objective via run config from a documented allow-list (e.g. net profit
  alone). Multi-objective fitness is out of 019 (Feature 022).
- **FR-006**: Runs MUST be reproducible from seed, grammar, data snapshot,
  config (including the chosen fitness id), and split parameters.
- **FR-007**: Minimum chronological train/validation/test split MUST accompany
  first UGE (021 min). During the run, fitness used for selection MUST be
  computed on **train** candles only. Validation metrics MAY be computed after
  the run for reporting. Test MUST NOT be used for selection; optional test
  report only after a phenotype is frozen.
- **FR-008**: Feature 019 MUST NOT place Real orders, enable Controlled Real,
  auto-start Simulation from UGE results, or start continuous live re-evolution.
  Invalid phenotypes MUST fail closed during evaluate (`EvaluationResult(ok=False)`);
  the run MUST NOT invent fitness or crash.
- **FR-009**: System MUST persist the best phenotype from an offline run and
  expose it as a **Backtest UI–selectable** program/strategy input (operator
  triggered). Side-by-side Strategy Comparison multi-run is **not** required
  for 019 DONE. MUST NOT auto-enable Simulation, Controlled Real, or autonomous
  trading from a UGE result.
- **FR-010**: 019 DONE for starting search is the Python `run_uge_search` entry
  (+ automated tests). A thin HTTP/CLI to start runs MAY be added but is not
  required. The Backtest UI requirement (FR-009) applies to **frozen**
  phenotypes, not to driving the evolutionary loop from the browser.

## Success Criteria

- **SC-001**: One offline UGE experiment completes and returns a phenotype
  string Feature 016 can Backtest.
- **SC-002**: For the configured fitness id, fitness for the best phenotype
  matches independent Feature 016 evaluate on the **train** candles within
  documented tolerance (prefer exact on fixed fixtures).
- **SC-003**: Replay with same seed/config/data reproduces the experiment
  outcome.
- **SC-004**: No crypto/exchange or CryptoAutoTrading strategy code is added
  inside FORGE `uge` (call/import only; no vendor copy).
- **SC-005**: Operator can select a persisted phenotype in the Backtest UI and
  obtain a completed Backtest without a running UGE process.

## Out of scope

- Rich experiment UI / full experiment lab (020 — Python `run_uge_search` is the
  search entry for DONE; frozen phenotype **Backtest** selection is in scope;
  Strategy Comparison multi-run deferred)
- Advanced multi-objective fitness (022)
- Regime-aware programs (023)
- Realtime continuous UGE during live markets
- Autonomous Real trading (024)
- Auto-start Simulation or Real from UGE results (015 remains paused)
- Torque capital allocation search (017)

## Assumptions

- Feature 016 evaluate bridge exists and is deterministic.
- FORGE path / editable install:
  [`docs/FORGE_INTEGRATION.md`](../../docs/FORGE_INTEGRATION.md)
  (`UGEEngine`, `Grammar`, `EvaluationResult`, `Fitness`).
- First data is recorded/historical candles (Feature 002 venue), not live
  private fills.
