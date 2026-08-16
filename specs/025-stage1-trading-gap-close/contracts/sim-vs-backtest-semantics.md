# Contract: Intentional Simulation vs Backtest semantics

**Feature**: `025-stage1-trading-gap-close`  
**Date**: 2026-08-16  
**Consumer**: Operators, tests, future Feature 015 readers

This note documents **intentional** differences. Feature 025 MUST NOT “fix”
these by forcing identical fill models.

---

## Intentional differences (keep)

| Topic | Simulation | Backtest |
|-------|------------|----------|
| Strategy / protective fill reference | Trustworthy **live mark** / last-price style at execution time | Historical **next candle open** (Feature 004) |
| Market context | Live closed candles + public quotes | Fixed historical candle series |
| Clock | Wall / worker poll (~2s) | Series iteration |

Protective TP/SL **inherit** the same fill models above after a high/low trigger.

---

## Must be consistent (fix if divergent)

| Topic | Rule |
|-------|------|
| TP/SL % config and absolute derivation from entry fill | Same formulas |
| High→TP / Low→SL triggers; entry-bar skip; SL before TP | Same |
| Exit precedence vs session stops / strategy | Same |
| Fees/slippage application on fills | Same economics helpers |
| Strategy signal meaning for identical OHLC series | Same strategy code |
| Cash/holdings updates from fills | Same Portfolio/accounting rules for Simulation; Backtest mirror of those economics |

---

## Explicitly not a bug

Different P&L between a live Simulation and a Backtest of “similar” conditions
when fill timestamps/prices differ because of mark vs next-open is **expected**.
Operators should compare like-for-like within one mode first, then interpret
cross-mode gaps using this table.
