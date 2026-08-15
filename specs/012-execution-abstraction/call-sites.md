# Call-site inventory: Execution Abstraction (012)

**Date**: 2026-08-15  
**Purpose**: Durable inventory of fill-related call sites for Feature 012.
Update this file when wiring changes; do **not** duplicate as a stale comment
in `backend/app/execution/__init__.py`.

## Production strategy-fill / forced-close paths

| Site | Role | Today | 012 target |
|------|------|-------|------------|
| `backend/app/simulation/pipeline.py` | Simulation strategy fills after Risk | Builds `ExecutionIntent`; `SimulationExecutionEngine.execute` | Keep `execute`; engine from `app.execution`; journal + Portfolio apply **after** fill |
| `backend/app/simulation/session_service.py` | Simulation forced-close / flatten fill | Uses `SimulationExecutionEngine` / `ExecutionIntent` | Keep mode-owned flatten orchestration; fill via Simulation adapter `execute` |
| `backend/app/backtest/engine.py` | Historical strategy fills + `_flatten` | `HistoricalExecutionAdapter.buy` / `.sell`; next-open `reference_price` in engine | Adapters from `app.execution`; `buy`/`sell` wrappers MUST call `execute` only; engine keeps next-open / flatten refs + journals |
| `backend/app/backtest/execution.py` | Historical adapter module | Full duplicated fill math + `HistoricalFillResult` | **Re-export only** from `app.execution.historical` (optional `HistoricalFillResult = FillResult` alias) |
| `backend/app/simulation/execution/port.py` | Simulation port + engine | Full fill math + `ExecutionEngine` Protocol | **Re-export only** from `app.execution` (no local fill bodies) |
| `backend/app/simulation/execution/simulation.py` | Re-export helper | Re-exports from port | Re-export from `app.execution` |

## Comparison (must not add a third fill path)

| Site | Role | Path |
|------|------|------|
| `backend/app/comparison/service.py` | Multi-leg comparison | `backtest_svc.run_leg_with_prefetched_candles` → `run_engine` → `HistoricalExecutionAdapter` |
| `backend/app/backtest/service.py` | Leg / run entry | Calls `run_engine` |

Comparison MUST NOT import fill math or invent a separate execution adapter.

## Out of scope for ExecutionEngine wiring

| Site | Note |
|------|------|
| `backend/app/backtest/metrics.py` | May use `buy_fill`/`sell_fill` for summary math — not a strategy-fill path; do not treat as a third adapter |
| Controller / Risk modules | Stay upstream of execution; adapters must not own them |

## Canonical package (012)

```text
backend/app/execution/
  port.py          # ExecutionIntent, FillResult, ExecutionEngine
  economics.py     # Shared buy/sell sizing + rejects (no price fetch)
  simulation.py    # SimulationExecutionEngine (runtime name; constitution “SimulationExecutionAdapter” is conceptual)
  historical.py    # HistoricalExecutionAdapter
  real.py          # RealExecutionAdapter stub
```
