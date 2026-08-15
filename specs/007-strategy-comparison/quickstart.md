# Quickstart: Strategy Comparison and Evaluation

**Feature**: `007-strategy-comparison`  
**Date**: 2026-08-12  
**Contracts**: [contracts/strategy-comparison-api.md](./contracts/strategy-comparison-api.md)  
**Data model**: [data-model.md](./data-model.md)

Validate fair multi-strategy comparison: shared candles and money assumptions,
2–5 registry legs, synchronous completion, inspectable comparison-originated
backtests (hidden from default history), no winner badge.

## Prerequisites

- Features 004–006 working (backtest engine, `/strategies`, ≥2 strategies)
- Backend and frontend per root README

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# second terminal
cd frontend && npm run dev
```

## Automated checks (preferred)

```bash
cd backend && source .venv/bin/activate

# Dual EMA / existing backtest continuity still green
pytest tests/unit/test_dual_ema_continuity.py -q

# Comparison unit + contract (paths as implemented)
pytest tests/unit/test_comparison_orchestrator.py \
       tests/unit/test_comparison_retention.py \
       tests/contract/test_comparison_api.py -q

# Shared-candle fairness / determinism
pytest tests/integration/test_comparison_shared_candles.py -q

# History default excludes comparison origin
pytest tests/contract/test_backtest_api.py -q -k "origin or comparison or list"

cd ../frontend && npm test -- --run src/__tests__/comparison
```

Expected: create with 2 legs returns completed comparison with both
`roundTripCount` and `fillCount`; reject `<2` / `>5` legs; no winner field;
default backtest list omits comparison-originated runs.

## Manual smoke

### 1) Create a two-strategy comparison

From Auto Trading → Comparison (or curl `POST /comparisons`) with a valid
window and legs `dual_ema` + `rsi` (defaults).

Expect: one response with `status: completed`, two leg rows, shared
`buyAndHoldReturnPct`, each leg has `backtestRunId`.

### 2) Inspect a leg

Open leg detail / `GET /backtest/runs/{backtestRunId}` + trades/decisions.

Expect: journals present; `origin` is comparison (or equivalent mark).

### 3) History filter

Open main backtest history (default).

Expect: comparison legs hidden. With include-comparison filter (if exposed),
legs appear and remain identifiable.

### 4) Reject bad selection

Submit with 1 leg or 6 legs → clear `400`. Submit invalid RSI params on one
leg → clear param error; no fabricated leaderboard.

### 5) No winner chrome

Completed table must not show “best” / “winner” based on return.

## Done when

- [X] Synchronous comparison of 2–5 strategies works on shared history
- [X] Required metrics including both round-trip and fill counts are visible
- [X] Leg backtests inspectable; default history hides comparison origin
- [X] Retention caps documented/enforced (10 completed / 5 failed comparisons)
- [X] Feature 004 single backtest path unchanged for manual runs
