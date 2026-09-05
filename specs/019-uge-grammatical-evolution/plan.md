# Implementation Plan: UGE Grammatical Evolution Search

**Branch**: `019-uge-grammatical-evolution` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature 019 — call FORGE `uge` (`UGEEngine` / `run`) to search Torque
phenotypes; this repo owns BNF, chronological train/val/test split (021 min),
and fitness via Feature 016 `evaluate_phenotype` → Feature 004 Backtest.
Offline/batch only; no Real; no FORGE source copy. FORGE path:
`/home/aghil/Documents/my document/limerick/projects/FORGE`.

## Summary

Add `backend/app/uge_search/` that:

1. Loads an MVP BNF (`Grammar.from_text` / `from_path`) over Feature 016 leaves
   (`rsi`, `macd`, `dual_ema`) + composition ops (`and` / `or` / `vote`) with
   discrete parameter alternatives.
2. Registers an evaluate callable that maps phenotype →
   `evaluate_phenotype(..., candles=train_slice)` →
   `Fitness([netProfit - buyAndHoldNetProfit], ["maximise"])`.
3. Runs `UGEEngine` (or `uge.run(EngineRunConfig)`) with fixed seed + candle
   snapshot; returns best phenotype + fitness; persists phenotype for frozen
   re-evaluation (US3).
4. Splits candles chronologically into train / validation / test; **selection
   uses train only**; validation reported after search; test held out
   (constitution XXXVIII / Feature 021 min).

Do not reimplement GE. Do not put crypto Backtest inside FORGE. Do not place
Real orders. Rich experiment lab (020) out of scope — offline run API + frozen
phenotype **Backtest UI** selection in scope (Session 2026-09-05). Strategy
Comparison multi-run deferred.

## Technical Context

**Language/Version**: Python 3.12 (backend + existing React frontend for Backtest
selection only). Starting a UGE search is the Python `run_uge_search` API
(+ tests); optional thin HTTP/CLI to *start* runs. Frozen phenotype **Backtest
UI** selection is **in scope** for 019 DONE (FR-009 / SC-005).

**Primary Dependencies**: FORGE editable `uge` (`UGEEngine`, `Grammar`,
`EvaluationResult`, `Fitness`, `EngineRunConfig`, `run`); Feature 016
`app.torque_bind.evaluate_phenotype`; Feature 004 Backtest via 016; pytest.

**Storage**: MVP — in-process + optional JSON result under
`backend/data/uge_runs/` (or tmp in tests). No full experiment DB (020).

**Testing**: pytest unit (grammar samples, split math, fitness adapter,
invalid phenotype → `EvaluationResult(ok=False)`); integration (tiny pop/ngen
seeded run completes; fitness matches standalone evaluate; seed replay);
import guard: `uge_search` must not import Real place path; Strategy modules
must not import `uge`.

**Target Platform**: Local developer machines (same as 016).

**Project Type**: Web application backend feature (`backend/`); docs under
`specs/019-uge-grammatical-evolution/`.

**Performance Goals**: Fixture UGE (small pop/ngen) completes in developer-
interactive time; production-scale search not an 019 SLO.

**Constraints**: Constitution XXXV–XXXVIII, XL; FR-001–FR-009; call FORGE only;
no Real; train-only selection; cost-aware fitness (fees/slippage via 016).

**Scale/Scope**: One MVP grammar; one fitness definition; one offline run entry
point; persist best phenotype; no multi-objective UI (022).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I Capital protection | Pass | No Real; Risk on Backtest path via 016 |
| II Simulation before real | Pass | Offline Backtest fitness only; 015 paused |
| III Single pipeline | Pass | Phenotypes → 016 → Controller/Risk |
| IV Controller / Risk | Pass | No bypass |
| VIII Fail safe | Pass | Invalid map/eval → failed EvaluationResult |
| X Intentional simplicity | Pass | Thin uge_search over FORGE + 016 |
| XII Evidence | Pass | Seeded fixture gates |
| XXXV Torque | Pass | Phenotypes are Torque strings; 016 binds |
| XXXVI GE | Pass | Call FORGE uge; own BNF + fitness |
| XXXVII Fitness | Pass | Explicit net − B&H; cost-aware |
| XXXVIII Leakage | Pass | Chronological train/val/test; select on train |
| XL Reuse | Pass | Reuse torque_bind + run_engine |

**Gate**: PASS.

### Post-design Constitution Check

PASS. Design keeps search operators in FORGE; fitness and BNF here; evaluate
only through 016; holdout unused for selection; Real untouched.

## Project Structure

### Documentation (this feature)

```text
specs/019-uge-grammatical-evolution/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── uge-search-api.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/app/uge_search/
├── __init__.py
├── grammar_mvp.py          # BNF text builder / load
├── grammars/
│   └── trading_mvp.bnf     # checked-in MVP grammar (discrete params)
├── splits.py               # chronological train/val/test
├── fitness.py              # phenotype → EvaluationResult (fitnessId allow-list)
├── runner.py               # UGEEngine / run wrapper (train-only selection)
├── persist.py              # best phenotype + run metadata JSON
├── phenotype_strategy.py   # Backtest-selectable torque phenotype Strategy
└── errors.py

backend/app/api/            # optional thin /uge/run + list frozen artifacts
frontend/src/features/backtest/  # select frozen phenotype / torque_phenotype

backend/tests/unit/test_uge_search_*.py
backend/tests/integration/test_uge_offline_run.py
frontend/src/__tests__/     # Backtest phenotype selection smoke if UI added

docs/FORGE_INTEGRATION.md   # already documents uge install
```

**Structure Decision**: `uge_search` backend package + minimal Backtest UI
wiring for frozen phenotypes. Reuse Feature 016 evaluate; do not fork GE.
Starting search = Python API (tests/smoke); rich experiment lab stays 020.

## Complexity Tracking

> No constitution violations requiring justification.
