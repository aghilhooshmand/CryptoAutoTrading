# Specification Quality Checklist: UGE Grammatical Evolution Search

**Purpose**: Planned-feature readiness (not implementation gate yet)  
**Created**: 2026-09-04  
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Focused on search ownership and offline-first evaluation
- [x] Mandatory sections present for a PLANNED feature
- [x] Clarifications from 2026-09-04 encoded
- [x] Clarifications from 2026-09-05 encoded

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain for the locked decisions
- [x] Requirements testable at plan/implement time
- [x] Realtime continuous search explicitly out of MVP
- [x] Leakage / train-val-test called out

## Notes

- Feature **016** Torque MVP is **DONE** — 019 implementation may proceed.
- Feature 015 Controlled Real remains paused until this sim/search MVP.
- Session 2026-09-05: default fitness `netProfit − buyAndHoldNetProfit` with
  configurable single-scalar allow-list; train-only selection; discrete BNF
  params; frozen phenotype selectable in Backtest UI (Comparison multi-run
  deferred). Sync `plan.md` / `research.md` before `/speckit-tasks` if needed.
