# Contract: Shared Risk Catalog

**Feature**: `010-advanced-risk-management`  
**Date**: 2026-08-14  
**Consumers**: Simulation pipeline, Backtest engine, decision/stop journals, UI

Stable **reason codes** are machine identifiers. **Messages** are operator-facing
and may be clarified without renaming codes. Journals store both fields.

## Precedence (Risk layer, first fail wins)

When reviewing a non-HOLD signal, evaluate in order and return the first
failure:

1. `emergency_stop_active`
2. Session inactive / already-triggered hard session stop context
3. `invalid_or_stale_market_data` (unsafe/missing mark)
4. `portfolio_max_loss_uncomputable` (BUY block) **or** `portfolio_max_loss` (stop)
5. `maximum_trades_reached` / `profit_target_already_reached` /
   `maximum_loss_already_reached` (session)
6. `conflicting_position_state`
7. `allocation_exposure_exceeded` (bound sessions only)
8. `per_symbol_exposure_exceeded` (when cap set)
9. Session sizing / `insufficient_balance` when evaluated at Risk  
   (else Execution retains `insufficient_balance` / dust codes)

Controller may reject earlier (`session_not_active`, emergency). Execution may
still reject after Risk approve.

## Existing codes (retain meaning)

| Code | Layer |
|------|--------|
| `emergency_stop_active` | controller / risk / stop |
| `session_not_active` | controller |
| `invalid_or_stale_market_data` | risk |
| `maximum_trades_reached` | risk / stop (`max_trades`) |
| `profit_target_already_reached` | risk / stop (`profit_target`) |
| `maximum_loss_already_reached` | risk / stop (`max_loss`) |
| `conflicting_position_state` | risk / execution |
| `insufficient_balance` | execution (and Risk if surfaced) |
| `duration_elapsed` | stop |
| `unrecoverable_unsafe_market_data` | stop |
| `hard_stop_flatten` | trade journal marker path |

## New portfolio-aware codes

| Code | Message (default) |
|------|-------------------|
| `insufficient_portfolio_available` | Allocated capital exceeds Portfolio available USDT. |
| `allocation_exposure_exceeded` | Trade would exceed the bound allocation’s reserved size. |
| `allocation_release_blocked` | Cannot release an allocation while a Simulation is bound to it. |
| `allocation_resize_blocked` | Cannot resize allocation below current deployed exposure. |
| `portfolio_max_loss` | Portfolio maximum loss bound reached. |
| `portfolio_max_loss_uncomputable` | Portfolio loss metric cannot be computed; new buys blocked. |
| `per_symbol_exposure_exceeded` | Trade would exceed the per-symbol weight cap. |

## Journal shape (unchanged envelope)

```json
{
  "reasonCode": "allocation_exposure_exceeded",
  "reasonMessage": "Trade would exceed the bound allocation’s reserved size."
}
```

`reasonCode` MUST be the catalog code. `reasonMessage` MUST NOT invent a
different semantic meaning for that code.
