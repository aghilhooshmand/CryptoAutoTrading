# Call-site inventory: Execution Abstraction (012)

**Date**: 2026-08-15  
**Updated**: 2026-08-15 (post-implement / convergence T042)  
**Purpose**: Durable inventory of fill-related call sites for Feature 012.
Update this file when wiring changes; do **not** duplicate as a stale comment
in `backend/app/execution/__init__.py`.

## Production strategy-fill / forced-close paths

| Site | Role | Current state (post-012) |
|------|------|--------------------------|
| `backend/app/simulation/pipeline.py` | Simulation strategy fills after Risk | Builds `ExecutionIntent`; calls `SimulationExecutionEngine.execute` (import via shim `app.simulation.execution.port` → `app.execution`); journal + Portfolio apply **after** fill |
| `backend/app/simulation/session_service.py` | Simulation forced-close / flatten fill | Mode-owned flatten orchestration; fill via `SimulationExecutionEngine.execute` (shim → `app.execution`) |
| `backend/app/backtest/engine.py` | Historical strategy fills + `_flatten` | Sets next-open / flatten `reference_price` in engine; calls `HistoricalExecutionAdapter.buy` / `.sell` which **only** wrap `self.execute` → shared economics; journals stay in engine |
| `backend/app/backtest/execution.py` | Historical adapter module | **Re-export only** from `app.execution.historical` (`HistoricalExecutionAdapter`, `HistoricalFillResult = FillResult` alias); zero local fill math |
| `backend/app/simulation/execution/port.py` | Simulation port shim | **Re-export only** from `app.execution` (`ExecutionIntent`, `FillResult`, `ExecutionEngine`, `SimulationExecutionEngine`); zero local fill math |
| `backend/app/simulation/execution/simulation.py` | Simulation shim | **Re-export only** from `app.execution` |

## Comparison (must not add a third fill path)

| Site | Role | Path |
|------|------|------|
| `backend/app/comparison/service.py` | Multi-leg comparison | `backtest_svc.run_leg_with_prefetched_candles` → `run_engine` → `HistoricalExecutionAdapter` (`app.execution` via backtest shim) |
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
  historical.py    # HistoricalExecutionAdapter (execute + buy/sell → execute only)
  real.py          # RealExecutionAdapter stub → real_execution_unavailable
```
