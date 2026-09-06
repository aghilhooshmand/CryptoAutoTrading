# Contract: Evolution Experiments API (Feature 020)

**Feature**: `020-evolution-experiments`  
**Date**: 2026-09-06  
**Phases**: 020a (required for first ship); 020b/020c fields noted  
**Depends on**: Feature 019 `uge_search`, FORGE `uge` reporters, Feature 016  
**Non-goals**: WebSockets; auto Real; raw BNF body; multi-objective

## Base path

Prefer extending `/uge/...` (existing 019 router) or `/evolution/...`.  
Vite proxy MUST forward the chosen prefix. This contract uses `/uge/experiments`.

## 020a — Create / control / observe

### `POST /uge/experiments`

Start an offline experiment (async).

**Request (JSON)** — minimum 020a:

```json
{
  "symbol": "btc_usdt",
  "timeframe": "1h",
  "startTime": "2024-01-01T00:00:00Z",
  "endTime": "2024-03-01T00:00:00Z",
  "populationSize": 8,
  "nGenerations": 3,
  "seed": 7,
  "fitnessId": "net_minus_bh",
  "trainRatio": 0.6,
  "valRatio": 0.2,
  "testRatio": 0.2,
  "startingCapital": "1000",
  "feeRate": "0.002",
  "slippageRate": "0.0005"
}
```

**020b optional fields** (ignored until 020b):

```json
{
  "leaves": ["dual_ema", "rsi", "macd"],
  "compositionOps": ["and", "or", "vote"],
  "paramAlternatives": {
    "rsi.period": [7, 14, 21],
    "dual_ema.fastPeriod": [5, 9, 12],
    "dual_ema.slowPeriod": [21, 26, 50]
  }
}
```

**Responses**:

| Status | Meaning |
|--------|---------|
| 202 | Accepted; body includes experiment summary with `id`, `status: "running"` or `"queued"` |
| 400 | Invalid config / insufficient candles / structured space invalid |
| 409 | Another experiment already active |

### `GET /uge/experiments`

List recent experiments (id, status, createdAt, bestPhenotype summary).

### `GET /uge/experiments/{id}`

Full experiment meta + embedded or linked generation summaries (at least
latest counts). While `running`, generations array grows.

### `GET /uge/experiments/{id}/generations`

Ordered list of `GenerationSnapshot` objects (0-based `generation` index).

### `POST /uge/experiments/{id}/cancel`

Cancel in-progress run. **200/202** with `status: "cancelled"` when accepted;
**409** if already terminal.

## Progress semantics (FR-004)

- Client MAY poll `GET .../generations` or parent resource every ~1s while
  `status === "running"`.
- Server MUST append a generation object when FORGE reporter completes that
  generation — **before** the overall run finishes.
- Optional SSE endpoint is non-blocking for DONE if poll works.

## Generation object (wire)

```json
{
  "generation": 0,
  "fitnessMax": 12.5,
  "fitnessAvg": 1.2,
  "fitnessMin": -3.0,
  "bestPhenotype": "dual_ema(fastPeriod=9, slowPeriod=21)",
  "recordedAt": "2026-09-06T01:00:00Z"
}
```

## Experiment terminal body (excerpt)

```json
{
  "id": "exp_…",
  "status": "completed",
  "bestPhenotype": "and(rsi(period=14), dual_ema(fastPeriod=9, slowPeriod=21))",
  "trainFitness": 12.5,
  "validationFitness": 8.0,
  "fitnessId": "net_minus_bh",
  "seed": 7,
  "terminationReason": "ngen",
  "generations": [ /* … */ ]
}
```

## Import / safety rules

- Experiment runner MAY import `uge` and `app.torque_bind` / `uge_search`.
- MUST NOT call Real place / confirmation APIs.
- Strategy / Controller / Risk MUST NOT import the experiment runner.

## Compatibility with 019

- `GET /uge/frozen` artifacts remain for Backtest free-text / artifact picker.
- 020a does **not** register named catalogue strategies (020c).
- Python `run_uge_search` remains valid for tests/CI.
