# Feature Specification: Evolution Experiments & Results (UGE Lab)

**Feature Branch**: `020-evolution-experiments`

**Created**: 2026-09-05

**Status**: Draft

**Input**: Operator wants a dedicated UI lab to run UGE, watch evolution
generation-by-generation with charts (FORGE-style inspectability), configure
grammar and strategy/operator space, freeze the best phenotype into the
strategy list, then manually choose that strategy in Backtest, Simulation, and
(when available) Real trading. Delivery is **three parts**: 020a → 020b → 020c.
Operator lock 2026-09-05: **UGE lab now** (ahead of resuming 015).

## Delivery Phases *(mandatory)*

| Phase | Name | Operator outcome |
|-------|------|------------------|
| **020a** | Run & watch | Configure usual UGE/search parameters on fixed MVP grammar; start/cancel; **stream each generation**; generation charts; show best phenotype; persist experiment results — **no** named strategy catalogue freeze (that is 020c) |
| **020b** | Grammar & search space | **Structured** controls: choose eligible strategy leaves and composition operators (`and` / `or` / `vote`); edit discrete parameter alternatives from product-safe lists; system builds grammar — **no raw BNF editor** in the UI |
| **020c** | Freeze into strategies | Freeze **best** phenotype as a **separate named strategy** (own list id + display name); operator picks it in Backtest / Simulation / Real like any other strategy — lab never auto-places Real orders |

Phases are independently demonstrable; later phases build on earlier ones.
Feature 020 is not DONE until all three phases meet their success criteria.

**Execution order (operator lock):** Implement and validate **020a → 020b → 020c**
in that sequence. User-story priority tags (e.g. US4 P1) do **not** override
this phase order—US4/020c ships after US3/020b.

## Clarifications

### Session 2026-09-06

- Q: After freeze with a display name, how should the entry appear in the
  strategy list for Backtest / Simulation / Real? → A: **Option A** — each
  freeze is a **separate named strategy** (own id + display name; phenotype
  stored with it), not merely a preset under one shared Torque type.
- Q: When is the operator allowed to freeze a phenotype into a named strategy?
  → A: **Option A** — freeze only when the run is **terminal** (completed,
  failed after some generations, or cancelled) and a best phenotype exists;
  no mid-run freeze while evolution is still in progress.
- Q: If freeze uses a display name that already belongs to another frozen
  strategy, what happens? → A: **Option A** — **reject**; keep the existing
  strategy; operator must choose another name (no overwrite, no auto-suffix).
- Q: In 020b, how should the operator change grammar and search space? → A:
  **Option B** — **structured only**: leaf/operator checkboxes and discrete
  param alternative lists; system builds the grammar; no raw BNF editing in
  the UI for this feature.
- Q: For 020a alone, is named-strategy freeze in scope? → A: **Option A** —
  **020a** = configure, start/cancel, stream generations, charts, persist
  experiment results (show best phenotype); **named strategy freeze = 020c
  only**.

### Session 2026-09-05 (operator)

1. Priority vs 015 → **UGE lab now**.
2. Scope → **all of 020a+b+c**, delivered in three parts.
3. Progress → **stream each generation** (live updates while run is in progress).
4. Reuse → **freeze and add to strategy list**; operator chooses Backtest /
   Simulation / Real; no auto-enable of Real from the lab.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure and start a UGE experiment (Priority: P1) — Phase 020a

An operator opens an Evolution / Experiments area (not buried only inside
Backtest), sets search parameters commonly used for UGE (population size,
generations, seed, fitness scalar from the allow-list, train/validation/test
split ratios, market symbol/timeframe/window, capital/fee/slippage as needed),
and starts an offline historical search. The system validates inputs and begins
evolution without requiring a separate Python shell.

**Why this priority**: Without startable experiments in the product UI, 019’s
Python-only entry remains the only path and the operator request is unmet.

**Independent Test**: From the UI alone, start a short seeded run on known
historical candles; run reaches a terminal state with a best phenotype or a
clear failure reason.

**Acceptance Scenarios**:

1. **Given** valid experiment parameters and available historical candles,
   **When** the operator starts the experiment, **Then** the system accepts the
   run and shows it as in progress.
2. **Given** invalid parameters (e.g. empty window, illegal split ratios),
   **When** the operator starts, **Then** the system rejects with a clear
   message and does not start evolution.
3. **Given** an in-progress experiment, **When** the operator cancels,
   **Then** the run stops at the **next generation boundary** (cancel latency
   ≈ time to finish the current generation’s evaluations) and is marked
   cancelled (partial results retained if any generations completed).

---

### User Story 2 - Watch evolution stream and charts (Priority: P1) — Phase 020a

While a run is active, the operator sees **each generation as it completes**
(generation index, best fitness so far, and summary statistics such as best /
mean / worst train fitness for that generation). Charts update to show fitness
progress over generations. When finished, the operator sees the best phenotype
string and key metrics (train; validation reported; test only if configured for
final report / after freeze policy from 019).

**Why this priority**: Streaming + charts are the stated reason to prefer a lab
over frozen-only Backtest picking.

**Independent Test**: During a multi-generation run, the UI updates at least
once per completed generation before the run ends; final screen shows best
phenotype.

**Acceptance Scenarios**:

1. **Given** a running experiment with N generations, **When** generation k
   finishes, **Then** the operator sees generation k results without waiting
   for generation N.
2. **Given** a completed experiment, **When** the operator views results,
   **Then** they see a fitness-over-generations chart and the best phenotype
   text.
3. **Given** a failed generation evaluation batch, **When** the run cannot
   continue, **Then** the UI shows a failure state and last successful
   generation data if any.

---

### User Story 3 - Shape grammar and allowed leaves/operators (Priority: P2) — Phase 020b

The operator uses **structured controls** to choose **which strategy leaves**
may appear, **which composition operators** (`and` / `or` / `vote`) may appear,
and discrete parameter alternatives from product-safe lists. The system builds
the effective grammar from those choices. There is **no raw BNF text editor**
in the UI for this feature. Empty leaf sets or invalid constructed search
spaces are rejected before start.

**Why this priority**: Expands search control beyond fixed MVP BNF; depends on
020a run/watch working.

**Independent Test**: Restrict leaves to a subset; confirm phenotypes only use
allowed leaves/ops; change discrete param alternatives via structured UI and
see them available in produced phenotypes over a short run.

**Acceptance Scenarios**:

1. **Given** only `dual_ema` and `rsi` selected as leaves and only `and` as
   composition, **When** evolution runs, **Then** produced phenotypes do not
   introduce disallowed leaves or operators.
2. **Given** structured controls that would yield an empty or invalid search
   space, **When** the operator starts, **Then** the system refuses to start
   and explains the problem.
3. **Given** no leaves selected, **When** the operator starts, **Then** the
   system refuses to start.

---

### User Story 4 - Freeze phenotype into strategy list for Backtest / Simulation / Real (Priority: P1) — Phase 020c

After an experiment reaches a **terminal** state (completed successfully,
failed after at least one generation, or cancelled) and a best phenotype
exists, the operator **freezes** the experiment’s **best phenotype** with a
display name. Freezing a non-best individual from the run is out of scope for
020 MVP. Freezing while evolution is still in progress is not allowed. The
system creates a
**separate named strategy** in the strategy catalogue (own id + display name;
phenotype stored with that entry)—not only a preset under a shared Torque type.
The operator can then create Backtest runs, Simulation sessions, and (when Real
execution is available) Real sessions using that strategy—same Controller /
Risk path as other strategies. The Evolution lab itself never places Real
orders.

**Why this priority**: Closes the loop from search to reusable trading
configuration without auto-trading from UGE.

**Independent Test**: Freeze → appear in strategy catalogue → Backtest and
Simulation create succeed with that id; Real create uses the same strategy
picker when Real is enabled (or is documented gated until 015).

**Acceptance Scenarios**:

1. **Given** a terminal experiment with a best phenotype, **When** the
   operator freezes it with a name, **Then** a new distinct strategy catalogue
   entry appears (own id + that display name) and can be selected in Backtest.
2. **Given** a frozen strategy, **When** the operator starts Simulation with
   it, **Then** the session uses that Torque phenotype for signals.
3. **Given** Real trading is available in the product, **When** the operator
   selects the frozen strategy for a Real session, **Then** the system treats
   it like any other strategy (subject to Real safety gates)—the lab does not
   auto-start Real.
4. **Given** freeze without a name or with a display name already used by
   another frozen strategy, **When** the operator submits, **Then** the system
   rejects clearly and leaves the existing strategy unchanged.
5. **Given** an experiment still in progress, **When** the operator attempts
   to freeze, **Then** the system refuses until the run is terminal and a best
   phenotype exists.

---

### Edge Cases

- Historical candle window too short for warmup / split → reject before start.
- Operator disconnects mid-run → run continues server-side; UI can reconnect and
  catch up to latest generation.
- Concurrent start while another experiment is running → reject or queue per
  Assumptions (single active run).
- Freeze with a display name already used by another frozen strategy → reject;
  existing entry unchanged.
- Freeze while run still in progress → refuse until terminal + best phenotype.
- Freeze of phenotype that fails Torque check → refuse freeze with error.
- Very long runs → operator can cancel; charts remain for completed generations.
- Real path not yet available → freeze still works for Backtest/Simulation;
  Real selection appears when Real feature is enabled without re-freezing.

## Requirements *(mandatory)*

### Functional Requirements

**Phase 020a**

- **FR-001**: System MUST provide a dedicated Evolution / Experiments UI area
  where the operator can configure and start UGE search without using a Python
  shell.
- **FR-002**: System MUST accept configurable UGE/search parameters including
  at least: population size, number of generations, random seed, fitness
  allow-list choice, chronological train/validation/test split ratios, and the
  market candle window (symbol, timeframe, range).
- **FR-003**: System MUST run evolution offline on a fixed historical candle
  snapshot for that experiment (no live-market re-search loop in this feature).
- **FR-004**: System MUST stream progress so the operator sees results for
  **each completed generation** while the run is still in progress.
- **FR-005**: System MUST present generation-oriented charts (at least fitness
  over generations: best and a central tendency such as mean).
- **FR-006**: System MUST show the best phenotype (and its train fitness) when
  a run completes successfully; validation metrics MUST be reportable without
  having influenced selection (per Feature 019 policy).
- **FR-007**: System MUST allow the operator to cancel an in-progress
  experiment; cancel MUST take effect by the **next generation boundary**;
  cancelled runs MUST NOT be presented as successful completion.
- **FR-008**: System MUST persist enough experiment identity and results for
  reproducibility (seed, config, grammar identity, phenotype, fitness,
  generation summaries, runtime, termination reason). Phase **020a** MUST NOT
  require registering a named strategy catalogue entry (that is **020c**).

**Phase 020b**

- **FR-009**: System MUST let the operator shape the experiment search space
  via **structured UI controls** (eligible leaves, composition operators, and
  discrete parameter alternative lists within product-safe bounds). The system
  MUST build the effective grammar from those controls.
- **FR-009a**: The Evolution UI MUST NOT require or expose a raw BNF grammar
  text editor for Feature 020 (raw/file grammar remains an implementation /
  advanced concern outside the operator UI).
- **FR-010**: System MUST allow the operator to choose which registered
  strategy leaves and which composition operators (`and`, `or`, `vote`) are
  eligible for that experiment.
- **FR-011**: System MUST reject start when the structured selection cannot
  produce a valid search space (including no leaves selected).

**Phase 020c**

- **FR-012**: System MUST let the operator freeze the experiment’s **best
  phenotype** from a **terminal** experiment (completed, failed after some
  generations, or cancelled) that has a best phenotype into a **separate named
  strategy catalogue entry** (own strategy id + display name; phenotype bound
  to that entry—not only a preset under one shared Torque strategy type).
  System MUST NOT allow freeze while the experiment is still in progress.
  Freezing a non-best individual is out of scope for 020 MVP.
- **FR-012a**: Display names for frozen strategies MUST be unique among frozen
  strategy entries; a freeze that reuses an existing frozen display name MUST
  be rejected without modifying the existing entry.
- **FR-013**: Those frozen strategies MUST be selectable in Backtest and
  Simulation configuration the same way other strategies are selected (listed
  alongside built-in strategies such as Dual EMA).
- **FR-014**: When Real-money session creation exists in the product, frozen
  strategy entries MUST be selectable there under the same Real safety rules as
  other strategies; the Evolution lab MUST NOT place or confirm Real orders by
  itself.
- **FR-015**: Freezing MUST fail closed if the phenotype fails Torque check /
  bind validation.

**Cross-cutting**

- **FR-016**: Evolution MUST continue to call FORGE UGE for search and
  CryptoAutoTrading Backtest/evaluate for fitness (no vendoring FORGE source;
  no moving trading semantics into FORGE).
- **FR-017**: Train-only selection and holdout test policy from Feature 019
  remain in force unless explicitly changed in a later feature.
- **FR-018**: Feature 020 MUST NOT auto-start Simulation or Real sessions from
  a search result; operator action is required for each trading mode.

## Key Entities *(include if feature involves data)*

- **Evolution Experiment**: Configured search job (parameters, grammar ref,
  leaf/operator allow-list, candle window, status, timestamps, termination).
- **Generation Snapshot**: Per-generation summary (index, best/mean/worst or
  equivalent fitness stats, timestamp) streamed to the operator.
- **Experiment Result**: Best phenotype, fitness values by split role, charts
  source data, reproducibility metadata.
- **Frozen Strategy Entry**: A first-class strategy catalogue row (stable
  strategy id, **unique** display name among frozen entries, validated Torque
  phenotype, provenance such as experiment id / seed), selectable like
  built-in strategies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can start a short UGE experiment from the UI and see
  the first generation’s summary within the time needed to evaluate that
  generation’s population (no need to wait for the full run to see gen 1).
- **SC-002**: For a completed multi-generation run, the UI shows one charted
  fitness series with one point per generation and the final best phenotype in
  under one minute of browsing after completion.
- **SC-003**: After freeze, a distinct named strategy appears in the strategy
  catalogue (own id) and can complete one Backtest and one Simulation
  create+run path using that entry on the same day without editing phenotype
  text by hand.
- **SC-004**: With a restricted leaf/operator set (020b), a sample of produced
  phenotypes (or the best phenotype) uses only allowed leaves and operators in
  100% of checked cases in acceptance testing.
- **SC-005**: Starting Real from the Evolution lab with one click is impossible;
  Real use requires choosing the frozen strategy in the Real/session flow when
  that flow exists.

## Assumptions

- Operator is a single trusted local/operator user (same trust model as the
  rest of the app); no multi-tenant ACL in 020.
- Streaming / “stream each generation” means the operator sees **per-generation
  updates** while the run is in progress; the product transport is **HTTP
  polling** of persisted generation snapshots (optional SSE later)—not
  WebSockets.
- At most **one** Evolution experiment runs at a time in a deployment; a second
  start is rejected with a clear message until the first finishes or is
  cancelled.
- Phase 020a ships run/stream/charts/persist on the default MVP grammar;
  **named strategy freeze is 020c only** (020a may show best phenotype text
  without catalogue registration).
- Phase 020b adds **structured** leaf/operator/discrete-param controls
  (system-built grammar; no raw BNF UI).
- Raw BNF editing is out of scope for the Evolution operator UI in 020.
- Feature **015** Controlled Real may still be incomplete when 020c lands; FR-014
  is satisfied by wiring the strategy picker where Real create already exists,
  or by accepting freeze + Backtest/Simulation first with Real selection gated
  until 015 enables it—without blocking 020c freeze/list work.
- Continuous live-market UGE and multi-objective fitness remain out of scope
  (later roadmap / Feature 022).
- Rich FORGE notebook visuals are a reference for **inspectability**, not a
  requirement to embed FORGE UI code.

## Out of Scope

- Auto-trading or auto-confirming Real orders from UGE.
- Multi-objective Pareto search (022).
- Copying or vendoring FORGE / UGE / Torque source into this repository.
- Replacing Feature 019 Python `run_uge_search` (it may remain for tests/CI).
- Strategy Comparison multi-run orchestration beyond normal strategy selection
  (unless already available for any strategy).
- Raw BNF grammar text editor in the Evolution UI (020b is structured controls
  only).
