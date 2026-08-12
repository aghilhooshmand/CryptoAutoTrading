# Feature Specification: Trading & Experiment Defaults

**Feature Branch**: `008-trading-experiment-defaults`

**Created**: 2026-08-12

**Status**: Planned

**Input**: User description: "Trading & Experiment Defaults: add a Settings area for local operator defaults used when creating Simulation, Backtest, and Strategy Comparison configurations. Support defaults for symbol, timeframe, starting capital, allocated capital, maximum position size, fee rate, slippage rate, optional target net profit rate, optional maximum loss rate, optional maximum trades, preferred strategy, and effective strategy parameters. Strategy defaults must use the existing strategy registry and dynamic parameter schemas rather than hard-coded strategy-specific settings. Forms should initialize from these defaults but operators can override them for each run. Settings are defaults only: every Simulation Session, Backtest Run, and Strategy Comparison must continue to persist its own effective configuration so later settings changes never alter historical runs or reproducibility. Provide reset-to-default behavior and validation using the same domain constraints as the corresponding trading forms. Keep settings local/single-operator for v1; no cloud sync, user profiles, exchange credentials, API keys, real-money enablement, secrets, or trading authority. Changing a setting must never start, stop, modify, or authorize trading. Keep the UI responsive around 375px and integrate Settings without creating a new trading engine or bypassing Controller → Risk → Execution."

## Clarifications

### Session 2026-08-12

- Q: When a new Strategy Comparison form opens, how should the saved preferred strategy and its parameters be applied to the comparison legs? → A: Prefill only the first leg from Settings; additional required legs use product/registry starters
- Q: When should create forms re-apply Settings values relative to in-progress edits? → A: Apply on fresh form open only; never overwrite an in-progress draft
- Q: How should the operator persist changes made on the Settings screen? → A: Explicit Save required; unsaved edits do not affect create forms (explicit Reset as well)
- Q: When the operator changes the preferred strategy on Settings, what happens to strategy parameter fields before Save? → A: Reset params to the new strategy’s registry defaults in the Settings draft
- Q: If optional target profit / max loss rates are unset in Settings, how should a new Simulation form behave? → A: Keep optional in Settings; Simulation leaves those fields empty when unset and enforces its own required-field validation at create/start
- Q: What happens to unsaved Settings edits when the operator leaves the Settings tab without Save or Reset? → A: Keep the unsaved draft in Settings tab state until Save, Reset, or full page reload; switching Auto Trading tabs does not auto-save or auto-discard; create forms still use only last successfully saved Settings
- Q (analyze remediation): How should fail-closed Settings reads surface to the operator? → A: When saved Settings cannot be used and the system fails closed to starters, the Settings UI MUST show a clear recovery warning with the starter values

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save reusable trading defaults (Priority: P1)

As a local operator, I want a Settings area where I set my usual trading
defaults (pair, timeframe, capital nesting, costs, optional risk limits, and
preferred strategy with parameters) so that Simulation, Backtest, and Strategy
Comparison forms open already filled with those values instead of blank or
hard-coded starters.

**Why this priority**: Repeated re-entry of the same money and market defaults
is the main friction this feature removes; without saved defaults, later
stories add little value.

**Independent Test**: Open Settings, save a valid set of defaults, reload the
Settings view, and confirm the same values are still present.

**Acceptance Scenarios**:

1. **Given** the operator has not saved custom defaults yet, **When** they open
   Settings, **Then** they see product starter values for the supported fields
   and can edit them.
2. **Given** the operator enters a valid defaults set and saves (explicit Save),
   **When** they leave Settings and return later on the same machine, **Then**
   the saved values are shown again.
3. **Given** the operator edits Settings but has not saved, **When** they open
   a fresh create form, **Then** that form initializes from the last
   successfully saved Settings (or product starters), not the unsaved draft.
4. **Given** the operator edits Settings but has not saved, **When** they
   switch to another Auto Trading tab and later return to Settings without a
   full page reload, **Then** the unsaved Settings draft is still present
   (not auto-saved and not auto-discarded).
5. **Given** the operator chooses a preferred strategy, **When** they edit
   strategy parameters, **Then** the parameter fields follow that strategy’s
   registry schema (labels, types, and constraints) rather than fixed Dual EMA
   or other hard-coded fields.
6. **Given** the Settings draft shows strategy A with parameters, **When** the
   operator switches preferred strategy to B before Save, **Then** parameter
   fields are replaced with strategy B’s registry defaults (editable before
   Save).
7. **Given** saved Settings could not be loaded and the system fails closed to
   product starters with a recovery warning, **When** the operator opens
   Settings, **Then** the UI shows that warning together with the starter
   field values.

---

### User Story 2 - New configurations start from Settings (Priority: P1)

As a local operator, I want Simulation, Backtest, and Strategy Comparison
create forms to initialize from my saved Settings so that starting a new run
takes fewer edits while still allowing per-run overrides.

**Why this priority**: Applying defaults at create time is the user-visible
payoff of storing Settings; equal priority to saving because both are needed
for an MVP.

**Independent Test**: Save distinctive Settings values, open each of the three
create forms, and confirm initial fields match Settings; change one field on a
form and submit without changing Settings.

**Acceptance Scenarios**:

1. **Given** saved Settings with a distinctive symbol and capital nesting,
   **When** the operator opens a new Simulation configuration form, **Then**
   those fields are pre-filled from Settings.
2. **Given** the same saved Settings, **When** the operator opens a new Backtest
   configuration form, **Then** shared market, money, cost, optional risk, and
   preferred strategy fields initialize from Settings.
3. **Given** the same saved Settings, **When** the operator opens a new Strategy
   Comparison configuration form, **Then** shared market/money/cost/optional
   risk fields initialize from Settings, the **first leg** is prefilled with the
   preferred strategy and its Settings parameters, and any additional required
   legs use product/registry starters (not a forced copy of the preferred
   strategy). The operator must still complete a valid 2–5 leg comparison.
4. **Given** a form initialized from Settings, **When** the operator overrides
   one or more fields and creates a session/run/comparison, **Then** the
   persisted effective configuration for that artifact reflects the overrides,
   not necessarily the Settings values.
5. **Given** the operator has an in-progress create draft with edits, **When**
   Settings are changed elsewhere or the operator briefly leaves and returns
   without clearing the draft, **Then** the draft fields are not overwritten by
   Settings.
6. **Given** optional target profit and maximum loss rates are unset in saved
   Settings, **When** the operator opens a fresh Simulation configuration form,
   **Then** those fields remain empty and Simulation’s own required-field
   validation still applies before create/start (Backtest/Comparison continue to
   treat omitted rates as unset/not applied).

---

### User Story 3 - Defaults never rewrite history (Priority: P1)

As a local operator, I want changing Settings after I have already created
sessions or runs to leave those historical configurations untouched so that
results stay reproducible and auditable.

**Why this priority**: Constitution and roadmap require Settings to be
copy-on-create only; violating this would break trust in journals and
comparisons.

**Independent Test**: Create a backtest (or simulation) with known effective
values, change Settings to different values, reopen the historical result, and
confirm the stored configuration is unchanged.

**Acceptance Scenarios**:

1. **Given** a completed Backtest Run with effective fee and capital values,
   **When** the operator later changes fee and capital defaults in Settings,
   **Then** viewing that run still shows the original effective values.
2. **Given** a Simulation Session and a Strategy Comparison already created,
   **When** Settings change, **Then** those artifacts’ stored configurations
   remain unchanged.
3. **Given** Settings change, **When** the operator creates a *new*
   configuration afterward, **Then** the new form initializes from the updated
   Settings.

---

### User Story 4 - Validate and reset Settings safely (Priority: P2)

As a local operator, I want invalid Settings rejected with clear reasons and a
way to reset to product starter defaults so that bad defaults cannot quietly
seed unsafe or impossible configurations.

**Why this priority**: Safety and recoverability matter, but saving and applying
valid defaults deliver the core value first.

**Independent Test**: Attempt to save invalid capital nesting and confirm
rejection; use reset and confirm starter defaults return without starting any
trading activity.

**Acceptance Scenarios**:

1. **Given** Settings with capital nesting that violates
   `0 < max position size ≤ allocated capital ≤ starting capital`, **When** the
   operator tries to Save, **Then** the save is rejected with a clear reason and
   prior valid saved Settings remain in effect for create forms.
2. **Given** optional risk fields are blank, **When** the operator Saves,
   **Then** those optionals remain unset (same “omitted means not applied”
   semantics as the trading forms).
3. **Given** custom Settings are saved, **When** the operator chooses
   reset-to-default and confirms, **Then** Settings return to product starter
   values (saved as active) and no simulation, backtest, or comparison is
   started, stopped, or modified.

---

### Edge Cases

- Invalid strategy parameters for the preferred strategy → save rejected with
  the same class of constraint messages used on trading forms.
- Preferred strategy change in Settings draft → parameter fields reset to the
  newly selected strategy’s registry defaults (not carried over from the
  previous strategy).
- Preferred strategy becomes unknown or removed from the registry → Settings
  surface a clear problem; operator must pick a currently registered strategy
  before saving; create forms must not invent strategy-specific hard-coded
  parameters.
- Partial / corrupted local Settings → fail closed to product starter defaults
  for form initialization and Settings display, with a clear UI indication
  (API `warning`) that saved Settings could not be used.
- Unsaved Settings draft → survives Auto Trading tab switches until Save,
  Reset, or full page reload; never becomes active create-form defaults until
  Save succeeds.
- Optional fields left empty → treated as unset, not as zero. For Simulation,
  unset optional risk rates in Settings do not auto-fill the form; Simulation
  create/start validation remains responsible for requiring session boundaries
  when the Simulation workflow requires them.
- Operator clears a required field → save blocked until required defaults are
  valid.
- Changing Settings while a create form draft is in progress → open draft fields
  stay as the operator left them; Settings apply only on the next fresh form
  open.
- Changing Settings while a simulation is running → Settings update (if valid)
  does not stop, start, flatten, or alter that session’s effective
  configuration.
- Phone-width (~375px) layout → Settings remain usable without hover-only
  controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a Settings area where the local operator
  can view and edit trading/experiment defaults used when creating new
  Simulation, Backtest, and Strategy Comparison configurations.
- **FR-002**: Settings MUST support defaults for: symbol, timeframe, starting
  capital, allocated capital, maximum position size, fee rate, slippage rate,
  optional target net profit rate, optional maximum loss rate, optional
  maximum trades, preferred strategy identity, and that strategy’s effective
  parameters.
- **FR-003**: Strategy-related Settings MUST be driven by the existing strategy
  registry and each strategy’s dynamic parameter schema. The system MUST NOT
  hard-code strategy-specific Settings fields for individual strategies. When
  the preferred strategy identity changes in the Settings draft, strategy
  parameter fields MUST reset to that strategy’s registry defaults (operator
  may edit before Save).
- **FR-004**: Simulation, Backtest, and Strategy Comparison create forms MUST
  initialize applicable fields from current Settings when opened for a **fresh**
  create draft (empty / first paint after navigate-to-create or after a
  successful create/discard that clears the draft). Settings MUST NOT overwrite
  an in-progress draft while the operator is editing it, even if Settings change
  elsewhere or the tab is briefly left and returned with the draft still active.
  The operator MUST be able to override any initialized field before create. For
  Strategy Comparison, Settings preferred strategy and parameters MUST seed
  **only the first leg**; additional legs MUST initialize from product/registry
  starters unless the operator changes them.
- **FR-005**: Settings are defaults only. Every Simulation Session, Backtest
  Run, and Strategy Comparison MUST persist its own effective configuration at
  creation time. Later Settings changes MUST NOT alter historical artifacts or
  their reproducibility.
- **FR-006**: Settings changes MUST require an explicit Save to become the
  active defaults used by fresh create forms. Unsaved Settings edits MUST NOT
  affect create-form initialization. Unsaved Settings draft state MUST persist
  across Auto Trading tab switches until Save, Reset, or full page reload
  (no auto-save and no auto-discard on tab leave). Saving MUST apply the same
  domain validation rules used by the corresponding trading forms (including
  capital nesting and strategy parameter constraints). Invalid Save MUST leave
  the last successfully saved Settings in effect.
- **FR-007**: The operator MUST be able to explicitly reset Settings to product
  starter defaults (with confirmation). Reset MUST persist those starters as
  the active saved Settings (or equivalent cleared-custom state that yields
  starters) and MUST NOT start, stop, or modify trading.
- **FR-008**: Changing, saving, or resetting Settings MUST NEVER start, stop,
  modify, flatten, authorize, or otherwise control trading activity.
- **FR-009**: Settings for v1 MUST remain local to the single-operator machine
  experience. The feature MUST NOT add cloud sync, multi-user profiles,
  exchange credentials, API keys, real-money enablement, secrets storage, or
  trading authority.
- **FR-010**: Settings MUST live within the existing product areas (normally
  under Auto Trading) and MUST NOT introduce a fourth primary navigation area.
- **FR-011**: The Settings experience MUST remain usable at approximately 375px
  width without hover-only critical controls.
- **FR-012**: This feature MUST NOT create a second trading engine and MUST NOT
  bypass Controller → Risk → Execution authority for any trading mode.
- **FR-013**: Target net profit rate, maximum loss rate, and maximum trades
  remain optional in Settings. When unset, fresh Backtest and Comparison forms
  MUST treat them as omitted (not applied). When unset, a fresh Simulation form
  MUST leave those fields empty and MUST continue to enforce Simulation’s own
  required-boundary rules at create/start rather than inventing rates from
  Settings.
- **FR-014**: When Settings load fail-closed to product starter values because
  saved Settings could not be used, the Settings UI MUST display a clear
  recovery warning to the operator while showing those starter values.

### Key Entities

- **OperatorDefaults (Settings)**: The local operator’s reusable default values
  for market, money, costs, optional risk limits, preferred strategy, and
  strategy parameters. Used only to initialize new configurations.
- **ProductStarterDefaults**: Built-in fallback values used when no valid
  saved Settings exist and when the operator resets Settings.
- **Effective Configuration**: The concrete configuration stored on a
  Simulation Session, Backtest Run, or Strategy Comparison at create time;
  independent of later Settings edits.
- **Preferred Strategy Selection**: A registry strategy identity plus
  schema-valid effective parameters stored in Settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After an explicit successful Save of valid Settings, a new
  Simulation configuration form opens with those defaults pre-filled in one
  visit (no retyping of the saved fields). Unsaved Settings edits do not
  pre-fill forms.
- **SC-002**: The same saved Settings pre-fill applicable fields on new
  Backtest forms, and on new Strategy Comparison forms (shared fields plus
  first leg only from preferred strategy).
- **SC-003**: After a historical Simulation, Backtest, or Comparison exists,
  changing Settings and reopening that historical artifact shows the original
  effective configuration unchanged.
- **SC-004**: Invalid capital nesting or invalid strategy parameters cannot be
  saved; the operator receives a clear reason in the Settings UI.
- **SC-005**: Reset restores product starter defaults and does not create,
  stop, or modify any trading session or historical run.
- **SC-006**: An operator can complete view → edit → save of Settings on a
  phone-width (~375px) layout without hover-only controls.
- **SC-007**: Completing Settings work never requires exchange trading
  credentials and never places real orders.

## Assumptions

- Feature 003–007 create forms already exist under Auto Trading; this feature
  supplies shared initialization defaults rather than replacing those workflows.
- Product starter defaults may mirror today’s form starters (for example pair
  `btc_usdt`, timeframe `1h`, capital nesting of 1000, and a registered
  preferred strategy such as Dual EMA with registry defaults) unless product
  copy later chooses different starters.
- Comparison still requires 2–5 legs; Settings supply shared market/money/cost
  /optional risk defaults and seed only the first leg’s preferred
  strategy/params; remaining legs use product/registry starters (not a
  multi-leg template library).
- Historical window start/end for backtests and comparisons remain per-run
  choices in v1 (not stored as Settings), unless a later feature extends
  defaults.
- Grammatical Evolution / experiment population defaults (seed, population
  size, generations) are out of scope for this feature despite appearing as
  future roadmap ideas.
- “Local / single-operator” means durable persistence on the operator’s
  environment without accounts or sync. The implementation plan locks the
  mechanism (local database-backed Settings API as source of truth — not
  browser-only prefs). Create forms and Settings UI consume that saved
  document after explicit Save.
- Settings placement is a secondary surface under Auto Trading (Settings tab),
  consistent with constitution primary-area limits.
- Simulation-only fields not listed in FR-002 (for example session duration)
  remain per-form concerns in v1 and are not stored in Settings.
- Validation messages should be understandable to the operator and aligned in
  meaning with Simulation/Backtest/Comparison form validation.
