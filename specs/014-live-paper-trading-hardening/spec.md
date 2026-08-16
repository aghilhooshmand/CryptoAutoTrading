# Feature Specification: Live Paper-Trading Hardening

**Feature Branch**: `014-live-paper-trading-hardening`

**Created**: 2026-08-16

**Status**: Draft

**Input**: Feature 014 — Harden the existing live-market Simulation / paper-trading system for reliable long-running operation and recovery. Reuse the single pipeline (Market Data → Strategy → Controller → Risk → Execution → Simulation Portfolio / Accounting). Do not create a second paper-trading engine. Cover restart/recovery, reconciliation before trading resumes, fail-closed unsafe recovery, duplicate candle/event/decision/fill prevention, duplicate-trade prevention after restart/retry, stale market data, temporary public XT/network failures, bounded retry where safe, Portfolio/accounting consistency, `unsafe_unflattened` and interrupted-state behavior, emergency stop under degradation, long-running reliability, operator-visible recovery/degraded/interrupted states, observability, and responsive UI (~375px). Out of scope: XT real place/cancel, RealExecutionAdapter activation, Real trading mode, real money, autonomous real trading, withdrawals/transfers, Torque, GE, new strategies, Backtest redesign.

## Clarifications

### Session 2026-08-16

- Q: After a backend restart, should an interrupted Simulation automatically resume trading, wait for explicit operator confirmation, or auto-resume only when reconciliation proves a safe state? → A: Conditional safe auto-recovery (Option C): auto-resume only after deterministic reconciliation proves the session safe; otherwise fail closed into non-trading `RECOVERY_BLOCKED` requiring operator action.
- Q: Which exact conditions must all pass before a recovered Simulation is allowed to trade again after restart? → A: Full ledger + watermark + Portfolio reconciliation (Option A): session cash & position consistent with trade journals; watermark consistent with last journaled trade/decision event; Simulation Portfolio binding & holdings agree with session position/cash; no unresolved `unsafe_unflattened` (or equivalent); trustworthy market data when an open position requires valuation. Any mismatch fails closed and prevents auto-resume.
- Q: What should happen to closed candles that completed while the backend was offline? → A: Skip (Option B): do not generate decisions or fills for the offline gap; on successful reconciliation, advance the processing watermark past missed closed candles, record the skipped gap for audit/observability, and resume with the next newly closed candle.
- Q: When recovery cannot safely continue, what exact session outcome should the system use? → A: Dedicated non-trading `RECOVERY_BLOCKED` state (Option B): neither `RUNNING` nor normal `STOPPED`; no automatic trading; operator action required; any attempt to resume the same session must pass the full reconciliation gates again; operator may instead stop/close the session or start a new one.
- Q: If market data stays stale or unavailable while a Simulation still has an open position, what should the system do? → A: Option C: block new entries immediately; keep the existing bounded unsafe-mark streak; if the streak is exhausted, stop strategy trading; flatten only with a trustworthy safe mark; otherwise preserve the open position as `unsafe_unflattened` with no invented exit price and clear operator visibility.

## Behavior locks (non-negotiable)

1. **Single pipeline** — harden Simulation paper trading in place; no second trading engine.
2. **Never invent** market prices, missed fills, decisions, or Portfolio/accounting state.
3. **Never resume trading** unless deterministic reconciliation establishes a safe state under the locked gate set (Clarifications Session 2026-08-16).
4. **Controller and Risk remain authoritative**; strategies remain advisory only.
5. **Simulation Portfolio (009)** remains the Simulation accounting book; **Real XT (013)** stays separate and unused for paper fills.
6. **RealExecutionAdapter** stays unavailable for live exchange fills; no Real trading mode.
7. **Recovery policy (locked)**: conditional safe auto-recovery — after backend restart, auto-resume trading only when deterministic reconciliation proves the session safe; otherwise fail closed into non-trading **`RECOVERY_BLOCKED`** (neither `RUNNING` nor normal `STOPPED`) requiring operator action. Silent always-resume and always-orphan-to-STOPPED-without-recovery-path are rejected.
8. **Duplicate processing must not produce another trade** — build on (and strengthen) the existing candle watermark `last_processed_candle_open_time` and journal integrity.

## Repository baseline (authoritative today)

Documented for planners; not a commitment to keep forever:

- Startup today runs `recover_orphan_sessions` (orphans → `STOPPED` + `backend_restart`; no auto-resume). Feature 014 **replaces/extends** that baseline with conditional safe auto-recovery per Clarifications Session 2026-08-16.
- Session states today: `CONFIGURED` → `RUNNING` → `STOPPING` → `STOPPED`. Feature 014 introduces fail-closed **`RECOVERY_BLOCKED`** (non-trading; not normal `STOPPED`) when reconciliation cannot prove safety.
- Candle dedupe watermark: `last_processed_candle_open_time`.
- Unsafe mark streak (limit 3) can stop with `unrecoverable_unsafe_market_data`.
- Public XT Spot adapter: timeout/errors fail the fetch; **no** public retry loop (unlike private XT 429 policy in 013).
- Simulation mark safety today primarily requires `MarketStatus.FRESH` on successful quotes; age-based Dashboard STALE (60s) is not the same path.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Survive backend restart without unsafe trading (Priority: P1)

As an operator, I want active Simulations handled safely across a backend restart so the system never invents state or silently continues trading from an unproven ledger.

**Why this priority**: Restart safety is the core gap deferred from Features 003/011 and the primary capital-protection risk for long-running paper trading.

**Independent Test**: Start a Simulation, kill/restart the backend, observe session disposition and that no new fills occur until a safe recovery/resume path (if any) is proven; journals and Portfolio are not fabricated.

**Acceptance Scenarios**:

1. **Given** a Simulation was `RUNNING` when the backend process stopped, **When** the backend starts again, **Then** the system does not invent prices, fills, or decisions for the downtime gap.
2. **Given** restart recovery runs, **When** a safe continuing state cannot be proven, **Then** trading does not resume; the session enters non-trading **`RECOVERY_BLOCKED`** (neither `RUNNING` nor normal `STOPPED`) requiring operator action.
3. **Given** deterministic reconciliation proves the session safe, **When** conditional safe auto-recovery applies, **Then** trading may resume for that same recoverable session without a separate confirmation click; otherwise it MUST NOT.

---

### User Story 2 - Prevent duplicate trades after restart or retry (Priority: P1)

As an operator, I want each closed candle / trading decision to be processed at most once so a restart or retry cannot double-fill the same event.

**Why this priority**: Duplicate fills would corrupt Simulation Portfolio and session economics.

**Independent Test**: Process a candle to a fill; simulate restart/retry with the same candle still “latest”; assert no second fill/decision for that watermark; journals remain consistent.

**Acceptance Scenarios**:

1. **Given** a candle open time has already been processed for a session, **When** the worker sees that candle again after restart or retry, **Then** no additional strategy→execution fill is produced for that candle.
2. **Given** a decision or fill was already journaled for an event identity, **When** recovery or retry re-enters the pipeline, **Then** duplicate decision/fill rows for the same event are not created.
3. **Given** the last-processed watermark is missing or inconsistent with journals, **When** recovery evaluates the session, **Then** the system fails closed into `RECOVERY_BLOCKED` rather than guessing the cursor.
4. **Given** closed candles elapsed while the backend was offline and reconciliation succeeds, **When** the session resumes, **Then** no decisions or fills are generated for that gap; the watermark is advanced past the missed closed candles; the skipped gap is recorded for audit; and processing continues only with the next newly closed candle.

---

### User Story 3 - Reconcile before any post-recovery trading (Priority: P1)

As an operator, I want session ledger, journals, and Simulation Portfolio to be reconciled into a consistent, inspectable picture before any post-recovery trading is allowed.

**Why this priority**: Today restart can leave Portfolio holdings while the session is force-stopped with `unsafe_unflattened`, which is unsafe to “just continue.”

**Independent Test**: Construct mismatched session vs Portfolio fixtures; run recovery/reconcile; assert trading blocked (`RECOVERY_BLOCKED`) until FR-006 gates pass or fail-closed outcome is recorded.

**Acceptance Scenarios**:

1. **Given** session cash/position and Simulation Portfolio disagree after interruption, **When** recovery reconciliation runs, **Then** the disagreement is detected, auto-resume is blocked, and trading does not proceed on invented corrections.
2. **Given** any locked gate fails (journals, watermark, Portfolio, unresolved unsafe flatten, or untrustworthy mark with open position), **When** the operator inspects the session, **Then** the session is in non-trading **`RECOVERY_BLOCKED`** with an inspectable reason, distinguishable from normal `STOPPED` completion.
3. **Given** all locked reconciliation gates pass, **When** conditional safe auto-recovery applies, **Then** subsequent fills continue to update session journals and Simulation Portfolio through the existing pipeline only.
4. **Given** a session is `RECOVERY_BLOCKED`, **When** the operator attempts to resume the same session, **Then** the full reconciliation gate set MUST pass again before trading; alternatively the operator may stop/close the session or start a new one.

---

### User Story 4 - Handle stale data and temporary public market failures (Priority: P1)

As an operator, I want stale quotes and temporary XT public/network failures to fail closed or retry only within safe bounds—never invent marks or force unsafe flattens with fake prices.

**Why this priority**: Long-running paper trading depends on public market data reliability without compromising capital protection.

**Independent Test**: Inject stale/failed quotes and transient API errors; assert no invented marks; assert open-position policy (FR-011); assert public retries stay within plan bounds (max 1 retry; 0.5s default backoff; Retry-After ≤2.0s) without duplicate trades.

**Acceptance Scenarios**:

1. **Given** market data cannot provide a trustworthy mark, **When** the Simulation evaluates risk or flatten, **Then** the system does not invent a price and does not claim a successful forced close without a safe mark.
2. **Given** a temporary public XT/network failure, **When** the system applies bounded retry (bounds set in plan), **Then** retries do not create duplicate trades or uncontrolled loops.
3. **Given** market data remains stale or unavailable while a position is open, **When** the bounded unsafe-mark streak is in progress, **Then** new entries are blocked immediately and no exit price is invented; **When** the streak is exhausted, **Then** strategy trading stops; flatten occurs only if a trustworthy safe mark exists, otherwise the position remains `unsafe_unflattened` and operator-visible.

---

### User Story 5 - Operate and observe long-running and degraded sessions (Priority: P2)

As an operator, I want visible recovery/degraded/interrupted status, emergency stop that still works under degradation, and enough logs/diagnostics to understand failures—on desktop and ~375px layouts.

**Why this priority**: Hardening is incomplete if operators cannot see or stop unsafe conditions.

**Independent Test**: Render session status for restart/degraded cases at ~375px; trigger emergency stop during degraded fetch; confirm diagnostic fields/codes without secret leakage.

**Acceptance Scenarios**:

1. **Given** a session interrupted by backend restart or failed recovery, **When** the operator opens Auto Trading / session detail, **Then** `RECOVERY_BLOCKED` (or equivalent API status) and stop/recovery reasons are visible and distinguishable from normal `STOPPED` completion.
2. **Given** market data or recovery is degraded, **When** the operator triggers emergency stop, **Then** new strategy-driven entries are prevented per existing emergency-stop intent.
3. **Given** a recovery or market failure occurs, **When** operators or maintainers inspect logs/diagnostics, **Then** stable reason codes and session identity are available without inventing missing economics.

---

### Edge Cases

- Backend dies mid-fill (journal vs Portfolio apply ordering mismatch).
- Backend dies during `STOPPING` / forced close.
- Multiple orphan rows if worker/DB race (still at most one active design).
- Watermark present but journals empty or journals ahead of watermark.
- Missed closed candles during downtime: **skip** — no decisions/fills for the gap; after successful reconciliation, advance watermark past missed closed candles, audit-log the skipped gap, resume on the next newly closed candle.
- Sustained XT public outage with flat vs long position: while long, block entries + unsafe-mark streak → stop strategy trading; flatten only with safe mark else `unsafe_unflattened`.
- `unsafe_unflattened` already set from prior unsafe flatten.
- Operator tries to “resume” a Feature 011 History STOPPED session id (must not bypass fail-closed rules).
- Emergency stop during recovery evaluation.
- Clock jump affecting freshness windows (observability; no silent invent).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Feature 014 MUST harden the existing Simulation paper-trading path only; it MUST NOT introduce a second independent paper-trading or live-trading engine.
- **FR-002**: All trading decisions MUST continue to follow Market Data → Strategy → Controller → Risk → Execution → Simulation Portfolio / Accounting.
- **FR-003**: The system MUST NOT invent market prices, missed fills, missed decisions, or Portfolio/accounting balances at any recovery or retry boundary.
- **FR-004**: On backend restart, active Simulations MUST be handled by an explicit recovery procedure that is fail-closed whenever a safe continuing state cannot be proven.
- **FR-005**: After backend restart, the system MUST apply **conditional safe auto-recovery**: auto-resume trading only when deterministic reconciliation proves the session safe; otherwise MUST fail closed into non-trading **`RECOVERY_BLOCKED`** (neither `RUNNING` nor normal `STOPPED`) that requires operator action before any further trading. Always-auto-resume without reconciliation and silent orphan→STOPPED without a recoverable path are forbidden.
- **FR-006**: Before any post-recovery trading is allowed, deterministic reconciliation MUST pass **all** of the following gates (any failure fails closed and prevents auto-resume): (a) session cash and position are consistent with trade journals; (b) last-processed watermark is consistent with the last journaled trade/decision event; (c) Simulation Portfolio binding and holdings agree with session position/cash; (d) no unresolved `unsafe_unflattened` (or equivalent unresolved flatten flag); (e) when an open position requires valuation, market data provides a trustworthy mark.
- **FR-007**: If reconciliation fails or is incomplete, the system MUST place the session in **`RECOVERY_BLOCKED`**, MUST block all automatic strategy-driven trading, and MUST require operator action. Any later attempt to resume the **same** session MUST re-run and pass the full FR-006 gate set; the operator MAY instead stop/close the session or start a new session. `RECOVERY_BLOCKED` MUST NOT be treated as normal History completion (`STOPPED`).
- **FR-008**: The system MUST persist a deterministic last-processed trading-event cursor (building on `last_processed_candle_open_time`) such that reprocessing the same candle/event cannot create another fill. After a successful skip of an offline gap (FR-010), the cursor MUST be advanced past missed closed candles before any new trading is allowed. Watermark updates and journal appends for the same logical event MUST be duplicate-safe across restart/retry.
- **FR-009**: Decision and trade journals MUST remain append-safe against duplicates for the same logical event identity after restart or retry.
- **FR-010**: Closed candles missed while the backend was offline MUST be **skipped**: the system MUST NOT generate decisions or fills for the offline gap. On successful reconciliation, the system MUST advance the processing watermark past those missed closed candles, MUST record the skipped gap for audit/observability, and MUST resume pipeline processing only with the next newly closed candle after that advanced watermark. Missing market history needed to identify the gap MUST fail closed rather than inventing skipped or replayed events.
- **FR-011**: Stale or untrustworthy market data MUST NOT be treated as a fresh executable mark. While a position is open and market data is stale/unavailable, the system MUST block new strategy-driven entries immediately and MUST continue to use the existing bounded unsafe-mark streak. When that streak is exhausted, the system MUST stop strategy trading. Flatten MUST occur only if a trustworthy safe mark exists; otherwise the system MUST preserve the open position as `unsafe_unflattened` with no invented exit price and MUST make the outcome operator-visible.
- **FR-012**: Temporary public market-data / network failures MAY retry only where safe and only within plan bounds: **at most one** automatic retry; default backoff **0.5s**; `Retry-After` wait capped at **2.0s** (if larger, do not retry). Retries MUST NOT create duplicate trades or uncontrolled loops and MUST NOT invent marks.
- **FR-013**: `unsafe_unflattened` and other interrupted/degraded outcomes MUST remain capital-safe (no fake flatten) and MUST be operator-visible with stop/recovery reasons.
- **FR-014**: Emergency stop MUST remain available during degraded market-data or recovery conditions and MUST prevent new strategy-driven entries.
- **FR-015**: Long-running Simulations MUST remain bounded by existing session risk/stop controls; Feature 014 MUST add reliability/recovery hardening without removing hard-stop authority.
- **FR-016**: Operators MUST be able to distinguish normal `STOPPED` completion from **`RECOVERY_BLOCKED`**, restart interruption, and degraded market-data conditions in the Simulation UI (including ~375px).
- **FR-017**: The system MUST emit sufficient structured diagnostics (stable codes, session id, recovery/reconcile outcomes) to explain fail-closed decisions without logging secrets.
- **FR-018**: Simulation Portfolio MUST remain the Simulation accounting source; Real XT account data MUST NOT be merged into Simulation books during recovery.
- **FR-019**: Strategies MUST remain advisory; Feature 014 MUST NOT grant XT private trading APIs or activate RealExecutionAdapter live fills.
- **FR-020**: Automated tests MUST cover: restart orphan handling under the chosen policy; duplicate-candle/event non-replay of fills; reconciliation pass/fail gates; stale/unavailable mark fail-closed; bounded retry without duplicate trades; emergency stop under degradation; operator-visible interrupted/degraded signals (or contract equivalents).

### Key Entities

- **Simulation session**: Lifecycle including `RECOVERY_BLOCKED`, cash/position, stop reasons, flatten status, watermark cursor.
- **Candle/event watermark**: Last processed or skip-advanced candle open time; prevents duplicate fills and offline-gap backfill.
- **Skipped-gap audit record**: Observability evidence of offline closed candles that were intentionally not traded.
- **Decision / trade journals**: Append-only evidence of intents and fills.
- **Simulation Portfolio book**: USDT/holdings/allocations bound to sessions — reconciliation subject.
- **Recovery outcome**: Pass (may auto-resume) vs fail-closed **`RECOVERY_BLOCKED`**.
- **Market-data health**: Fresh vs stale vs unavailable for marks (policy-dependent).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a controlled restart test with an active Simulation, 100% of post-restart outcomes are either **`RECOVERY_BLOCKED`** (no new fills; operator action required) or auto-resume only after deterministic reconciliation passes—never silent invent-and-trade and never always-resume without gates.
- **SC-002**: Re-presenting an already-processed candle/event after restart produces zero additional fills for that event in automated checks; a controlled offline gap under the skip policy produces zero decisions/fills for missed candles and leaves an audit record of the skipped range after watermark advance.
- **SC-003**: Fixture mismatches on any locked gate (journals, watermark, Portfolio, unresolved unsafe flatten, or untrustworthy mark with open position) are detected by reconciliation, prevent auto-resume, place the session in **`RECOVERY_BLOCKED`**, and yield zero invented balance corrections.
- **SC-004**: With untrustworthy marks while long, new entries are blocked immediately; after unsafe-mark streak exhaustion the system stops strategy trading and never records a forced close with an invented exit price—`unsafe_unflattened` remains when no safe mark exists.
- **SC-005**: Transient public market failure fixtures demonstrate bounded retry (when enabled by policy) without duplicate fills and without uncontrolled loops.
- **SC-006**: Operators can identify `RECOVERY_BLOCKED` and degraded sessions from UI or API status fields in a walkthrough at ~375px width, distinct from normal `STOPPED`.
- **SC-007**: Emergency stop during injected market-data degradation prevents new entries in automated or scripted checks.
- **SC-008**: Ordinary create/start/stop Simulation flows from Features 003/010/011 continue to work without requiring Real trading mode or XT private credentials.

## Assumptions

- Features 003, 009, 010, 011, 012, and 013 behaviors remain the baseline; Feature 014 extends Simulation reliability only.
- `last_processed_candle_open_time` is the current candle dedupe cursor to build on.
- Feature 011 History rule (normal `STOPPED` session id is not restarted as the same historical run) remains for terminal stops; **`RECOVERY_BLOCKED`** is a distinct non-trading state that may be operator-resumed only after full reconciliation, or stopped/closed / replaced by a new session.
- Public XT credentials are not required; private XT (013) is unused for paper fills.
- UI remains within Auto Trading / session detail patterns; no fourth primary nav item.

## Out of Scope

- XT real order placement or cancellation
- Activating RealExecutionAdapter for exchange fills
- Operator Real trading mode / real-money execution
- Autonomous real-money trading
- Withdrawals / transfers
- Torque / Grammatical Evolution
- New trading strategies
- Redesign of Backtest / Historical execution semantics
- Multi-active simultaneous Simulations (unless later clarification forces it; default remains single active)

## Open for Clarification *(session complete — remaining items deferred to plan)*

Locked in Clarifications Session 2026-08-16:

1. ~~Resume policy~~ **Locked**: conditional safe auto-recovery; else **`RECOVERY_BLOCKED`**.
2. ~~Reconciliation gates~~ **Locked**: full ledger + watermark + Portfolio; no unresolved unsafe flatten; trustworthy mark when open position needs valuation.
3. ~~Missed closed candles~~ **Locked**: skip; advance watermark; audit gap; resume on next newly closed candle.
5. ~~Stale while long~~ **Locked**: block entries; unsafe-mark streak; stop strategy trading on exhaustion; flatten only with safe mark else `unsafe_unflattened`.
7. ~~Fail-closed state~~ **Locked**: **`RECOVERY_BLOCKED`**.

**Deferred to `/speckit-plan` (question quota reached):**

4. Fine-grained watermark/journal persistence/transaction ordering beyond FR-008/FR-009/FR-010 — **Resolved in plan** [research.md](./research.md) R4 / [data-model.md](./data-model.md).
6. Exact temporary public-market failure retry counts and backoff bounds — **Resolved in plan** [research.md](./research.md) R5 / [contracts/public-market-retry.md](./contracts/public-market-retry.md): max 1 retry; 0.5s default backoff; Retry-After capped at 2.0s.

## Planning notes (non-normative)

- Today’s `recover_orphan_sessions` is the fail-closed baseline to extend carefully.
- Distinguish normal `STOPPED` (History inspect-only) from **`RECOVERY_BLOCKED`** (operator must resolve; same-session resume only after full gates).
- Align simulation mark freshness with constitution fail-closed rules; consider whether Dashboard 60s STALE semantics should apply to paper marks.
- Public XT retries should not copy private 429 trading semantics blindly—reads only, still no invent.
- Long-running tests: prefer deterministic simulated clocks/fixtures over live multi-hour CI.
