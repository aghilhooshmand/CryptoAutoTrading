# Feature Specification: Simulation History & Results

**Feature Branch**: `011-simulation-history-results`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "Feature 011 — Simulation History & Results: list/filter persisted Simulation sessions; reopen stopped/completed/interrupted runs; inspect effective configuration, strategy/parameters, trades, decision journal (including Risk rejection reasons), timestamps and stop reasons; freeze a final result snapshot at termination when valid valuation exists so later market prices cannot rewrite history; delete with confirmation and safe rules; preserve that navigation/refresh/remount do not stop an active backend Simulation; responsive operator UI. Out of scope: auto-resume after restart, crash recovery, Portfolio reconciliation after restart, unsafe_unflattened continuation, multi-active sessions, Feature 010 Risk semantic changes, XT private API, real-money execution. History is an inspection/persistence layer; Simulation execution/accounting remains authoritative."

## Clarifications

### Session 2026-08-15

- Q: For Simulation sessions that already stopped before this feature ships, how should final results be handled? → A: Best-effort backfill from persisted ledger only; never use current/new market prices for old stopped sessions; mark incomplete when a trustworthy stop-time valuation cannot be reconstructed.
- Q: If a never-started or already-stopped Simulation still references a Portfolio allocation that is holding reserved or deployed capital for that session, what should delete do? → A: Reject deletion while an active Portfolio allocation binding still has reserved or deployed capital; require normal release/resolution first; History deletion must not unwind Portfolio state.
- Q: When a Simulation stops without a trustworthy ending equity or P&L, should the system still store a final-result snapshot marked incomplete? → A: Always persist a final-result snapshot; mark it incomplete and keep unverifiable metrics null rather than inventing them.
- Q: From History, what actions may an operator take on a STOPPED Simulation besides inspect and delete? → A: STOPPED: inspect and delete only (no restart / no “run again” from History).
- Q: Where should Simulation History appear in the operator UI? → A: History list on the Simulation page, with a dedicated detail route/page for inspecting an individual historical simulation; no new top-level navigation item.
- Q: Analysis remediation 2026-08-15 — list order? → A: Locked to `created_at DESC, id DESC`.
- Q: Analysis remediation 2026-08-15 — list pagination? → A: Offset pagination: `limit` default 50, max 100; `offset` default 0; response includes `totalCount`; UI must fetch older sessions (no permanent silent truncate).
- Q: Analysis remediation 2026-08-15 — STOPPED economics? → A: With `finalResult`, frozen snapshot is sole authoritative ending economics; do not expose drifting live mark-based ending P&L on STOPPED History detail.
- Q: Analysis remediation 2026-08-15 — CONFIGURED vs STOPPED actions? → A: CONFIGURED may use existing Feature 003 Start; STOPPED is inspect + delete only; no restart/resume of same session id; no second start implementation.
- Q: Analysis remediation 2026-08-15 — detail route? → A: Locked to `/auto-trading/simulation/:sessionId`.
- Q: Analysis remediation 2026-08-15 — “recovery” meaning? → A: Existing fail-closed orphan→STOPPED plus result freeze/backfill; does not mean resume/restart/worker recreation.
- Q: **Decision Log Mode amendment (pre-011)**: How does History treat decision journals? → A: History shows only durably persisted decision-journal records; display effective `decision_log_mode` on detail/config; do not fabricate missing HOLD rows; `full_audit` may be candle-dense, `important_only` intentionally sparse. Backtest unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and reopen past Simulations (Priority: P1)

As an operator, I want a clear history of Simulation sessions (including state) so I can find a past run and reopen it to inspect what happened without starting a new Simulation.

**Why this priority**: Without list/reopen, persisted sessions are effectively invisible after leaving the live viewer; this is the core value of Feature 011.

**Independent Test**: With several STOPPED sessions and optionally one RUNNING session, open Simulation History, distinguish states, open a STOPPED session, and confirm config, journals, and timestamps match that session.

**Acceptance Scenarios**:

1. **Given** multiple persisted Simulation sessions in different states, **When** the operator opens Simulation History on the Simulation page, **Then** each session appears with enough identity (at least symbol, timeframe, strategy, state, start/stop times when set) to choose among them.
2. **Given** a STOPPED (or otherwise terminal) session, **When** the operator opens it from the History list, **Then** they land on a dedicated detail view for that session and see the effective configuration actually used for that run (capital bounds, fee/slippage, duration/max trades, optional Portfolio binding and portfolio risk fields when present), symbol, timeframe, strategy identity, and effective strategy parameters.
3. **Given** a session with trades and decision journal entries (including Risk rejections), **When** the operator inspects that session from history, **Then** trades and journal entries for that session are visible (only durably persisted decisions — no fabricated HOLDs), including rejection reasons where recorded, and the effective `decision_log_mode` is visible in configuration/detail.
4. **Given** a session that has started and/or stopped, **When** the operator views detail, **Then** start time, end time (when stopped), and stop/completion reason (when set) are visible.
5. **Given** an active RUNNING session, **When** the operator views History, **Then** that session is distinguishable as active/running and can be reached without implying a second simultaneous Simulation is allowed.
6. **Given** a STOPPED session opened from History at `/auto-trading/simulation/:sessionId`, **When** the operator views available actions, **Then** only inspection and (when eligible) delete are offered—not restart or resume on that historical session.
7. **Given** a CONFIGURED session opened from History, **When** the operator chooses Start, **Then** the existing Feature 003 start behavior is used (no second start implementation).
8. **Given** more sessions than one page, **When** the operator requests the next offset page, **Then** older sessions appear (`created_at DESC, id DESC`) and `totalCount` remains consistent.

---

### User Story 2 - Frozen final results that do not drift (Priority: P1)

As an operator, I want final economics of a finished Simulation frozen at termination (when a valid valuation existed) so later market price changes cannot rewrite historical P&L or ending equity.

**Why this priority**: Roadmap and constitution require trustworthy historical performance; live mark-to-market after stop would falsify past results.

**Independent Test**: Complete a Simulation with a valid terminal valuation; record shown final metrics; change underlying market prices; reopen history detail; confirm frozen final metrics are unchanged.

**Acceptance Scenarios**:

1. **Given** a Simulation terminates and a valid valuation is available at termination, **When** the system records final results, **Then** a frozen final-result snapshot is persisted (at least starting capital, ending equity/value used for the authoritative terminal P&L view, P&L, return, cumulative fees, cumulative slippage cost, and other justified terminal metrics such as trade counts and flatten status).
2. **Given** a session with a frozen final-result snapshot, **When** market prices later change and the operator reopens that session, **Then** the frozen final results remain unchanged.
3. **Given** a Simulation is still RUNNING, **When** the operator views live economics, **Then** live/mark-based economics may continue to update (history freeze applies at termination, not as a substitute for live monitoring).
4. **Given** termination occurs but a valid valuation is not available (for example open position without a safe mark), **When** final results are recorded, **Then** a final-result snapshot is still persisted, marked incomplete, with unverifiable ending equity/P&L left null (not invented), while truthful fields such as cash, fees, slippage, flatten status, and stop reason remain available.
5. **Given** a session that was already STOPPED before Feature 011, **When** History first materializes its frozen snapshot, **Then** backfill uses only persisted session ledger fields (no current/new market prices), always stores a snapshot, and marks it incomplete with null unverifiable metrics if stop-time valuation cannot be reconstructed trustworthily.

---

### User Story 3 - Delete historical Simulations safely (Priority: P2)

As an operator, I want to delete historical Simulations I no longer need, with explicit confirmation, without accidentally deleting or disrupting an active or unsafe-to-remove session.

**Why this priority**: History accumulates; deletion is necessary housekeeping but must not break active runs or Portfolio binding safety.

**Independent Test**: Attempt delete on RUNNING (rejected); delete STOPPED with confirmation (removed from list and not reopenable); confirm Portfolio allocations are not deleted merely because a historical session is deleted.

**Acceptance Scenarios**:

1. **Given** a STOPPED or never-started CONFIGURED session with no active Portfolio reserved/deployed binding, **When** the operator requests delete and confirms, **Then** that session and its session-scoped inspection data (trades, decisions, frozen snapshot) are removed and no longer appear in history.
2. **Given** a RUNNING or STOPPING session, **When** the operator attempts delete, **Then** deletion is rejected with a clear reason and the session remains.
3. **Given** any delete action, **When** the UI offers deletion, **Then** the operator must explicitly confirm before the delete proceeds.
4. **Given** a historical session that was once bound to a Portfolio allocation and that binding no longer holds reserved/deployed capital for the session, **When** that session is deleted after it is STOPPED, **Then** Portfolio capital/ledger state is not rewritten by history deletion (deletion is history cleanup, not Portfolio unwind).
5. **Given** a CONFIGURED or STOPPED session whose Portfolio allocation binding still has reserved or deployed capital for that session, **When** the operator attempts delete, **Then** deletion is rejected until normal release/resolution completes; History delete does not unwind Portfolio state.

---

### User Story 4 - Stay connected without stopping the backend run (Priority: P2)

As an operator, I want navigation away from Simulation, browser refresh, and frontend remount to leave an active backend Simulation running so I can return via active-session reconnect or History without an unintended stop.

**Why this priority**: Existing Feature 003 behavior must not regress when History UI is added.

**Independent Test**: Start a Simulation; navigate away / refresh; confirm session still RUNNING; return via active session or History and continue inspection.

**Acceptance Scenarios**:

1. **Given** a RUNNING Simulation, **When** the operator navigates within the app, refreshes the browser, or remounts the Simulation UI, **Then** the backend Simulation does not stop solely because of that frontend lifecycle event.
2. **Given** a RUNNING Simulation after refresh, **When** the operator returns to Simulation, **Then** they can reconnect to the active session (existing behavior preserved) and/or see it in History as active.

---

### User Story 5 - Responsive operator History UI (Priority: P3)

As an operator on a narrow viewport, I want History list and detail flows to remain usable so I can review past runs on typical laptop and ~375px-wide layouts.

**Why this priority**: Required by project UI standards for operator surfaces; secondary to correctness of freeze and list/reopen.

**Independent Test**: Exercise list → open → inspect → delete-confirm at ~375px width without loss of primary actions.

**Acceptance Scenarios**:

1. **Given** Simulation History on a ~375px-wide viewport, **When** the operator lists sessions on the Simulation page, opens a dedicated detail view, and confirms delete, **Then** primary actions remain reachable without horizontal scrolling of the whole page as the only way to proceed.
2. **Given** History list and dedicated detail views, **When** rendered on desktop width, **Then** state, identity fields, and frozen results (when present) are scannable without relying on hover-only information for critical facts.

---

### Edge Cases

- Termination with `unsafe_unflattened`: history remains inspectable; a final-result snapshot is still persisted and marked incomplete with null unverifiable equity/P&L; no inventing marks; no auto-continuation.
- Pre-existing STOPPED sessions (created/stopped before Feature 011): best-effort backfill of a frozen snapshot from persisted session ledger fields only; never fetch or apply current/new market prices for that backfill; mark incomplete when stop-time valuation cannot be reconstructed trustworthily (e.g. open position without a persisted stop-time mark).
- Backend restart that marks sessions STOPPED with restart reason (existing behavior): session appears in history as interrupted/stopped; no auto-resume in this feature.
- CONFIGURED session never started: appears in history (or filterable list); deletable; no frozen final results required.
- Empty history: clear empty state; create/start flow remains available elsewhere as today.
- Delete of last remaining historical session: list becomes empty; active RUNNING (if any) still listed/reachable.
- Filter by state with no matches: empty filter result, not an error.
- Session detail missing journals: show empty trades/decisions, not fabricated rows (including no fabricated HOLDs under `important_only`).
- History Decision Journal reflects effective `decision_log_mode` (`full_audit` may include HOLD history; `important_only` is sparse by design).
- Concurrent UI: attempting to start another Simulation while one is RUNNING remains rejected (multi-active still out of scope).
- Delete while Portfolio binding still has reserved/deployed capital for the session: reject; require normal release/resolution first; never unwind Portfolio via History delete.
- STOPPED from History: no restart / run-again; new Simulation requires a new session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operators MUST be able to list persisted Simulation sessions as a History list on the Simulation page, with each entry showing enough identity to distinguish runs (including state). The product MUST NOT add a new top-level navigation item solely for Simulation History. List MUST be ordered by `created_at DESC`, then `id DESC`, and MUST support offset pagination (`limit` default 50, max 100; `offset` default 0; response `totalCount`) so older sessions remain reachable.
- **FR-002**: Operators MUST be able to filter or otherwise clearly distinguish sessions by state (at least active/running vs terminal/stopped, and never-started configured when present).
- **FR-003**: Operators MUST be able to reopen any persisted session for inspection via the dedicated detail route `/auto-trading/simulation/:sessionId`, including STOPPED / completed / interrupted sessions and the single active session when present.
- **FR-024**: Opening a historical session from the Simulation-page History list MUST navigate to `/auto-trading/simulation/:sessionId` (config, journals, timestamps, frozen results); returning to the list MUST remain available without using a new top-level nav item.
- **FR-023**: For STOPPED sessions, History MUST offer inspection and (when delete-eligible) deletion only; History MUST NOT restart or resume a STOPPED session or “run again” under the same historical session identity. CONFIGURED sessions MAY use the existing Feature 003 Start action (reuse existing start behavior; MUST NOT create a second start implementation). New runs after STOPPED require creating a new session via the normal create/start flow.
- **FR-025**: For STOPPED sessions with a `finalResult`, that snapshot MUST be the sole authoritative ending economics in History/detail; the system MUST NOT expose current/live mark-based ending equity, net P&L, or return on STOPPED History detail in a form that can drift after termination.
- **FR-004**: Session inspection MUST expose the effective configuration actually used for that session (capital and session risk bounds, fee/slippage, duration and max trades, strategy identity and effective parameters, symbol and timeframe, **`decision_log_mode`**, and Feature 009/010 binding and portfolio risk fields when they were set on the session).
- **FR-005**: Session inspection MUST expose the trade journal for that session.
- **FR-006**: Session inspection MUST expose the decision journal for that session **as durably persisted** (including Risk rejection reason codes/messages when recorded). History MUST NOT fabricate missing HOLD decisions. Under `important_only`, the journal is intentionally sparse; under `full_audit`, candle-by-candle HOLD history may appear. Detail UI MUST show the effective `decision_log_mode`.
- **FR-007**: Session inspection MUST expose start timestamp, end timestamp when stopped, and stop/completion reason when set.
- **FR-008**: When a Simulation reaches a terminal STOPPED state, the system MUST persist a frozen final-result snapshot for that session (complete when valid valuation is available at termination; incomplete otherwise).
- **FR-009**: Frozen final-result snapshots MUST include at least: starting capital, ending equity/value used for the authoritative terminal P&L presentation (null when incomplete), net P&L (null when incomplete), return relative to starting capital (null when incomplete), cumulative fees, cumulative slippage cost, trade count (and strategy fill count when already tracked), position flatten status, stop reason, and a freeze completeness indicator.
- **FR-010**: After a frozen final-result snapshot exists, historical presentation of those final metrics MUST NOT change solely because current market prices changed.
- **FR-011**: When termination lacks a valid valuation for ending equity/P&L, the system MUST still persist the final-result snapshot marked incomplete; unverifiable metrics MUST remain null (MUST NOT invent values); truthful session facts (e.g. cash, fees, slippage, flatten status, stop reason) MUST remain available.
- **FR-021**: For sessions already STOPPED before Feature 011 is available, the system MUST best-effort backfill a frozen final-result snapshot from persisted session ledger fields only; it MUST NOT use current or newly fetched market prices for that backfill; a snapshot MUST always be stored; when a trustworthy stop-time valuation cannot be reconstructed, the snapshot MUST be marked incomplete with unverifiable metrics null.
- **FR-012**: Live economics for RUNNING sessions MAY continue to use current safe marks; this MUST NOT overwrite or replace a previously frozen final-result snapshot after stop.
- **FR-013**: Operators MUST be able to delete eligible historical sessions only after explicit confirmation.
- **FR-014**: Deletion MUST be rejected for sessions in RUNNING or STOPPING state.
- **FR-015**: Successful deletion MUST remove the session from History and remove session-scoped inspection data (trades, decisions, frozen snapshot) for that session.
- **FR-016**: Deleting a historical Simulation MUST NOT rewrite Portfolio ledger balances, MUST NOT delete Portfolio allocations, and MUST NOT unwind or release Portfolio reserved/deployed capital as a side effect of history cleanup.
- **FR-022**: Deletion MUST be rejected while the session’s Portfolio allocation binding still has reserved or deployed capital for that session; the operator MUST complete normal release/resolution before delete is allowed.
- **FR-017**: Frontend navigation, browser refresh, and Simulation UI remount MUST NOT by themselves stop an active backend Simulation (preserve current reconnect behavior).
- **FR-018**: Simulation History and detail UI MUST follow `docs/UI_UX_STANDARDS.md` (confirm destructive actions; usable primary flow around 375px; clear labels for SIMULATION vs other modes).
- **FR-019**: History MUST remain an inspection/persistence layer: Simulation execution and accounting remain the single authoritative engine; History MUST NOT introduce a second accounting engine or alternate fill ledger.
- **FR-020**: This feature MUST NOT add auto-resume after backend restart, crash recovery/worker reconstruction, Portfolio reconciliation after restart, continuation of `unsafe_unflattened` sessions, multiple simultaneous active Simulations, Feature 010 Risk semantic changes, XT private API usage, or real-money execution. Existing orphan **recovery** (RUNNING/STOPPING → STOPPED) remains fail-closed and MAY freeze/backfill final results; recovery MUST NOT resume or recreate workers for the stopped session.

### Key Entities

- **Simulation Session (existing)**: Persisted run identity and lifecycle (`CONFIGURED` / `RUNNING` / `STOPPING` / `STOPPED`), effective configuration fields, capital/position ledger fields, timestamps, stop reason, flatten status, optional Portfolio binding and portfolio risk fields. Reused as the History row source of truth.
- **Decision Journal Entry (existing)**: Per-evaluation record including signal, outcome, and rejection reasons (including Risk). Reused for inspection.
- **Trade Journal Entry (existing)**: Per-fill record with prices, fees, slippage, forced-close flag. Reused for inspection.
- **Frozen Final Result Snapshot (new)**: Immutable terminal economics captured once at eligible termination (and via pre-011 ledger-only backfill). Always persisted for STOPPED sessions; completeness flag distinguishes complete vs incomplete. Unverifiable ending equity/P&L/return remain null when incomplete. Bound 1:1 to a session; never recomputed from later market prices for historical display.
- **History List Item (derived)**: Operator-facing summary of a session for browsing (identity + state + time + optional frozen P&L summary when available).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a set of at least five persisted sessions spanning multiple states, an operator can locate a chosen STOPPED session on the Simulation-page History list and open its dedicated detail view in under two minutes without starting a new Simulation.
- **SC-002**: For a session frozen with complete terminal valuation, reopening after material market-price change shows the same frozen starting capital, ending equity/value, P&L, return, fees, and slippage as at freeze time (bit-for-bit equality of displayed final metrics).
- **SC-003**: 100% of delete attempts on RUNNING/STOPPING sessions are rejected; 100% of delete attempts while a session’s Portfolio binding still has reserved/deployed capital are rejected without changing Portfolio balances; 100% of confirmed deletes on otherwise eligible STOPPED/CONFIGURED sessions remove that session from subsequent History lists.
- **SC-004**: After navigation away and full browser refresh during a RUNNING Simulation, the session remains RUNNING and is reachable again without the refresh itself having issued a stop.
- **SC-005**: Primary History list (Simulation page) → dedicated detail → delete-confirm path is completable on a ~375px-wide viewport without losing access to confirm/cancel or back-to-list actions.
- **SC-006**: Operators can verify Risk rejection reasons on a historical session that had Risk rejections by reading the decision journal alone (no need to re-run the Simulation). Operators can see effective `decision_log_mode` and MUST NOT see fabricated HOLD rows that were never persisted.

## Assumptions

- Feature 003 already persists sessions, trades, and decision journals (subject to effective `decision_log_mode`); Feature 011 primarily adds History listing, deletion rules, terminal freeze, and operator UX on top of that persistence. Decision Log Mode is a Feature 003/008 amendment implemented before Feature 011 code.
- Authoritative Session NET P&L semantics from Feature 003 (liquidation-style equity when long) remain the basis for what “ending equity/value” means in a complete freeze; informational mark equity may be stored additionally only if it does not replace the authoritative terminal P&L.
- “Valid valuation” means the same safety conditions Feature 003 already uses for computable liquidation/mark equity at that moment (safe mark when a position is open; flat sessions can freeze from cash).
- Incomplete freeze is preferred over inventing prices when valuation is invalid at stop; a snapshot is always persisted for STOPPED sessions with unverifiable metrics left null.
- Pre-011 STOPPED sessions are backfilled from persisted ledger only (never current/new market prices); incomplete when stop-time valuation cannot be reconstructed.
- No automatic FIFO retention purge of Simulation history in this feature; operators delete explicitly (unlike Backtest’s completed/failed caps).
- CONFIGURED never-started sessions are included in History (filterable) and are deletable when otherwise eligible; they are not terminal history—CONFIGURED MAY use existing Feature 003 Start (reuse; no second start stack). STOPPED sessions are inspect/delete only from History (no restart/resume).
- At most one RUNNING/STOPPING Simulation remains a platform rule; History listing does not relax that rule.
- Portfolio binding release/unwind continues to follow Features 009/010 lifecycle only — History delete never unwinds Portfolio; delete is rejected while reserved/deployed capital remains for that session’s binding.
- Backend restart → STOPPED with restart reason remains existing Feature 003/recovery behavior; Feature 011 only freezes/backfills results for inspectability. **Recovery** means fail-closed orphan→STOPPED plus freeze — not resume/restart/worker recreation.
- UI copy continues to label Simulation distinctly from Live Paper and Backtest.
- History list lives on the Simulation page; individual inspection uses `/auto-trading/simulation/:sessionId`; no new top-level navigation item for Simulation History.
- List order locked: `created_at DESC, id DESC`. Offset pagination: limit default 50, max 100; offset default 0; `totalCount` returned.

### Planning inventory (for `/speckit-plan`; not implementation)

Identified before implementation, locked as planning inputs:

1. **Reusable persisted fields**: Session identity/lifecycle/config/position/economics accumulators (`starting_capital`, fees/slippage cumulatives, trade counts, timestamps, `stop_reason`, `position_flatten_status`, strategy id/params, **`decision_log_mode`**, Feature 009/010 fields); Decision Journal (mode-gated); Trade Journal.
2. **Freeze fields**: starting capital; authoritative ending equity/value; net P&L; return; fees; slippage; trade/strategy-fill counts; flatten status; stop reason; completeness flag; freeze time; optional informational mark equity/price only if stored without overriding authoritative P&L. Pre-011 backfill: ledger-only, never current market.
3. **Deletion rules**: reject RUNNING/STOPPING; reject while Portfolio binding still has reserved/deployed capital for the session; allow STOPPED and CONFIGURED after confirm once binding is clear; cascade session-scoped journals + snapshot; never unwind/rewrite Portfolio via History delete.
4. **Capability surfaces**: list (`state`, `limit`/`offset`/`totalCount`, order `created_at DESC, id DESC`), get detail (existing reopen enriched with freeze; STOPPED ending economics = finalResult only), delete; preserve active-session discovery for reconnect. No resume/restart-historical endpoints.
5. **Frontend UX**: History list on Simulation page with offset pagination (no new top-level nav); detail route `/auto-trading/simulation/:sessionId`; CONFIGURED may Start (reuse 003); STOPPED = inspect/delete only; show effective `decisionLogMode`; Decision Journal = persisted rows only (no fabricated HOLDs); frozen results block; delete confirm; keep live viewer reconnect; responsive per UI standards.
6. **Regression tests**: freeze immutability after price change; pre-011 backfill never uses current market; list order/filter/pagination; delete reject active / reject bound reserved-deployed / allow cleared stopped; refresh does not stop; Risk reject reasons visible on historical session; History does not fabricate HOLD rows; no Portfolio balance rewrite on history delete; no resume/restart/worker recreation introduced.

## Out of Scope

- Auto-resume after backend restart
- Crash recovery / worker reconstruction
- Portfolio reconciliation after restart
- Continuation of `unsafe_unflattened` sessions
- Multiple simultaneous active Simulations
- Feature 010 Risk semantic changes
- XT private API
- Real-money execution
- Second accounting engine or alternate fill ledger for History
