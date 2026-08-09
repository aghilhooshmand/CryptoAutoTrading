# Feature Specification: XT Spot Market Data

**Feature Branch**: `002-xt-market-data`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "Connect CryptoAutoTrading to XT.COM public Spot market-data APIs; retrieve pairs, latest price, 24h stats, and candlesticks; show real XT data on the Dashboard with clear source/status and fail-safe error handling; isolate XT behind an exchange adapter; no trading, credentials, sentiment, or portfolio."

## Clarifications

### Session 2026-08-09

- Q: For Feature 002, which XT Spot pairs should the Dashboard let the user choose from? → A: Only XT Spot pairs quoted in USDT
- Q: When market data becomes stale, what should the Dashboard show for the last known price and statistics? → A: Show last known values with a clear STALE status (not presented as fresh/current)
- Q: For historical candlesticks on the Dashboard in Feature 002, how should intervals work? → A: User can switch among a small set (15m, 1h, 4h, 1d)
- Q: How should the Dashboard refresh XT market data in Feature 002? → A: Manual refresh required for acceptance, plus optional light auto-refresh (for example every 30–60 seconds) if easy
- Q: After the user selects a trading pair, should that selection still be selected if they reload the Dashboard page? → A: Persist last selected pair and interval on the local device across reloads
- Q: Can users favorite pairs for quicker Dashboard selection? → A: Users can locally favorite supported XT USDT Spot pairs; favorites appear before the full searchable pair list; favorites persist on the local device; favoriting affects Dashboard market viewing only and MUST NOT imply portfolio ownership or Auto Trading configuration

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View genuine XT Spot market data on the Dashboard (Priority: P1)

A developer or operator opens the Dashboard and sees real public Spot market information sourced from XT for a supported trading pair, including the selected pair identity, latest price, basic 24-hour statistics when available, data source labeled as XT, and last-update timing when available. Placeholder-only market content from Feature 001 is replaced for this scope.

**Why this priority**: Without live public market data on the Dashboard, later trading and sentiment features have no factual market context to build on.

**Independent Test**: Run the app locally, open Dashboard, confirm XT-sourced pair, price, stats (when provided), source label, and update time without any credentials.

**Acceptance Scenarios**:

1. **Given** the application is running locally without exchange credentials, **When** the user opens Dashboard, **Then** they see market-data content for a supported XT Spot pair that is not fabricated placeholder pricing.
2. **Given** market data has been retrieved successfully, **When** the user views Dashboard, **Then** XT is clearly identified as the market-data source and a last-update time is shown when available.
3. **Given** 24-hour statistics are available from XT for the selected pair, **When** the user views Dashboard, **Then** they can see at least latest price plus available change, high, low, and volume fields without inventing missing values.
4. **Given** market data is visible on Dashboard, **When** the user triggers refresh, **Then** the system requests updated XT public data for the selected pair and updates price/stats/history or a clear failure/STALE status without fabricating values.

---

### User Story 2 - Select a supported XT Spot trading pair (Priority: P1)

The user can browse or choose among supported XT Spot trading pairs **quoted in USDT**, optionally mark pairs as local favorites, and update the Dashboard market view to that pair’s public data. Favorites are a Dashboard selection convenience only.

**Why this priority**: Pair selection is the primary control for which market the operator monitors.

**Independent Test**: From Dashboard, select a different supported pair and confirm price/stats/history update to that pair’s XT data (or a clear loading/error state).

**Acceptance Scenarios**:

1. **Given** XT Spot USDT-quoted trading pairs are available, **When** the user opens pair selection, **Then** they can identify and choose among those supported USDT pairs via a searchable list (non-USDT quote markets are not offered in Feature 002).
2. **Given** a supported pair is selected, **When** market data loads successfully, **Then** Dashboard shows that pair’s latest price and available 24h statistics sourced from XT.
3. **Given** the user selects an unsupported or unrecognized symbol, **When** the system attempts to load market data, **Then** the UI shows a clear unsupported/unavailable state and does not fabricate a price.
4. **Given** the user previously selected a supported pair and interval, **When** they reload the Dashboard, **Then** the last selected pair and interval are restored when still valid.
5. **Given** a supported USDT Spot pair is available, **When** the user favorites it, **Then** that pair appears in a favorites section before the full searchable pair list after reload on the same local device.
6. **Given** a pair is favorited, **When** the user views Auto Trading or Portfolio, **Then** no portfolio ownership, balances, positions, or Auto Trading configuration is implied or created by that favorite.

---

### User Story 3 - View historical candlestick/price history for the selected pair (Priority: P2)

For the selected pair, the user can view a simple historical price/candlestick presentation based on XT public K-line data and switch among a small set of intervals: 15 minutes, 1 hour, 4 hours, and 1 day.

**Why this priority**: History turns a single price into usable market context without requiring trading features.

**Independent Test**: With a supported pair selected and history available, confirm a simple historical presentation appears; with history unavailable, confirm a clear empty/error state without fake candles.

**Acceptance Scenarios**:

1. **Given** a supported pair is selected and XT returns historical candlestick data, **When** the user views Dashboard history, **Then** a simple historical price/candlestick presentation is shown for that pair at the active interval.
2. **Given** historical data is shown for one interval, **When** the user selects another allowed interval (15m, 1h, 4h, or 1d), **Then** history reloads for that interval without fabricating candles.
3. **Given** historical data is unavailable or fails, **When** the user views the history area, **Then** they see a clear unavailable/error state and no invented candles or prices.

---

### User Story 4 - Stay safe when XT data fails or is stale (Priority: P1)

When XT is unreachable, returns malformed data, omits fields, or data is stale, the product fails safely: no fabricated values, clear status to the user, and the rest of the app (navigation among primary areas) remains usable.

**Why this priority**: Constitution requires fail-safe behavior under uncertainty; market-data failures must not look like trustworthy live prices.

**Independent Test**: Simulate or force failure/stale/unsupported conditions and verify clear status messaging with no fabricated prices while Dashboard/navigation remain usable.

**Acceptance Scenarios**:

1. **Given** XT market data cannot be retrieved, **When** the user views Dashboard, **Then** they see a clear failure/unavailable status and no fabricated market values.
2. **Given** a response is malformed or missing critical fields, **When** the system processes it, **Then** it rejects unsafe use of that payload and surfaces a clear error/unavailable state rather than guessing.
3. **Given** previously shown data becomes stale under the feature’s freshness rules, **When** the user views Dashboard, **Then** last known price/statistics MAY remain visible but MUST be accompanied by a clear STALE status and MUST NOT be presented as fresh/current.
4. **Given** a market-data failure state, **When** the user navigates to Auto Trading or Portfolio, **Then** primary navigation still works.

---

### User Story 5 - Use market data on phone-width screens (Priority: P2)

On an approximately 375px-wide viewport, the user can still select/view a pair, read price and available stats, see source/status, and view the simple history presentation without desktop-only gestures.

**Why this priority**: Constitution requires phone-usable UI for operator monitoring.

**Independent Test**: Resize to ~375px and complete pair view + status readability for the Dashboard market-data section.

**Acceptance Scenarios**:

1. **Given** a phone-width viewport, **When** the user opens Dashboard market data, **Then** pair identity, price (or error status), source, and primary controls remain usable and readable.

---

### Edge Cases

- XT returns an empty USDT pair list → clear empty/unavailable state; no invented pairs.
- Selected pair becomes unsupported after a refresh → clear unsupported state; do not keep showing prior price as if still valid without status.
- Data becomes stale while last known values exist → keep values visible with explicit STALE status; do not present them as fresh/current.
- Partial 24h stats (some fields missing) → show available fields only; omit or mark missing fields; never invent numbers.
- Network timeout / XT outage → clear failure status; app remains navigable.
- User switches pairs quickly → UI must not permanently show the previous pair’s data labeled as the new pair (avoid mismatched pair/price).
- Historical series shorter than expected → show what XT returned; do not pad with fake candles.
- User switches candle interval quickly → UI must not permanently show the previous interval’s series labeled as the new interval.
- Persisted pair is no longer in the USDT-supported list after reload → fall back to default pair rules; clear status; do not fabricate prices for the old symbol.
- Favorited pair is no longer supported → remove or hide it from favorites; do not invent market data for it.
- Backend healthy but XT market adapter failing → health of the app process and market-data status MUST remain distinguishable where both are visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST retrieve public XT Spot trading pairs quoted in USDT without requiring user credentials or API keys. Non-USDT quote markets are out of selection scope for Feature 002.
- **FR-002**: Users MUST be able to select a supported XT Spot USDT-quoted trading pair for Dashboard market viewing.
- **FR-003**: The system MUST retrieve the latest public market price for the selected pair from XT.
- **FR-004**: The system MUST retrieve basic 24-hour public market statistics for the selected pair when XT provides them, including available fields among latest price, price change and/or percentage change, high, low, and volume.
- **FR-005**: The system MUST retrieve public historical candlestick/K-line data for the selected pair from XT for the active interval. The Dashboard MUST let the user switch historical interval among exactly 15 minutes, 1 hour, 4 hours, and 1 day. The default interval MUST be 1 hour.
- **FR-006**: The Dashboard MUST present, for this feature’s scope: selected trading pair, latest price, basic available 24h statistics, a simple historical price/candlestick presentation with the allowed interval control, market-data source/status, and last update time when available.
- **FR-007**: The Dashboard MUST clearly identify XT as the current market-data source when XT is the active source.
- **FR-008**: The system MUST NOT fabricate market values (prices, stats, candles, or pairs) when data is missing, stale, malformed, unsupported, or unavailable. When market data is stale, the Dashboard MUST show a clear STALE status; last known values MAY remain visible for context but MUST NOT be labeled or implied as fresh/current.
- **FR-009**: On XT API failure, unavailable data, malformed responses, unsupported symbols, or stale data, the system MUST fail safely and expose a clear user-visible status while keeping the application navigable.
- **FR-010**: Exchange-specific XT market-data access MUST be isolated behind an exchange/market-data adapter boundary so Dashboard presentation and non-exchange application logic do not depend directly on XT-specific APIs or types.
- **FR-011**: Where practical, the system MUST preserve traceability of market-data source identity and retrieval/observation timestamp for displayed market data.
- **FR-012**: Dashboard market-data presentation MUST remain usable on phone-width viewports (~375px) as well as desktop-width viewports.
- **FR-013**: Initial market-data access MUST use simple public request/response retrieval (not require real-time streaming). Streaming is out of scope unless a later clarification/plan explicitly adds it.
- **FR-014**: Completing this feature MUST NOT require XT authenticated/private APIs, API keys, account balances, open orders, order placement/cancellation, simulation trading, real-money trading, Trading Controller, Risk Manager, strategies, portfolio calculations, news, sentiment, Fear & Greed indexes, backtesting, AI/ML, futures, margin, or leverage.
- **FR-015**: The Dashboard MUST NOT, in this feature, add news, Fear & Greed, market/social sentiment, portfolio balances, positions, or trading controls.
- **FR-016**: The Auto Trading and Portfolio primary areas MAY remain placeholders for this feature; market-data functionality is Dashboard-scoped.
- **FR-017**: The Dashboard MUST provide an explicit user-triggered refresh of market data for the selected pair (and active history interval). Manual refresh is required for Feature 002 acceptance. Light automatic refresh (approximately every 30–60 seconds) MAY be included but is not required for acceptance.
- **FR-018**: The system MUST persist the user’s last selected supported trading pair and last selected historical interval on the local device so a Dashboard reload restores those choices when still valid. If the persisted pair is no longer supported, the system MUST fall back to the default pair selection rules and MUST NOT fabricate market data for the invalid symbol.
- **FR-019**: Users MUST be able to favorite and unfavorite supported XT USDT Spot pairs using local-device storage only (no accounts and no database/server preference store for favorites). Favorited pairs MUST appear before the full searchable pair list. Favoriting MUST affect Dashboard market-pair selection only and MUST NOT imply portfolio ownership, balances, positions, or Auto Trading configuration.

### Key Entities

- **Trading Pair**: A public XT Spot instrument quoted in USDT that the user can select (identity/symbol presentation suitable for humans).
- **Market Quote**: Latest price and available 24h statistics for a pair, with source and timing metadata.
- **Candlestick Series**: Ordered historical OHLC (or equivalent) points for a pair over one of the allowed public intervals (15m, 1h, 4h, 1d), with source and timing metadata. Default interval is 1h.
- **Market Data Status**: User-visible readiness of market data (e.g., fresh, loading, stale, unavailable, unsupported, error) without inventing values. For `stale`, last known values may still be shown alongside the status.
- **Exchange Market Data Adapter**: Logical boundary isolating XT-specific retrieval from the rest of the product.
- **Pair Favorite**: A locally stored mark on a supported XT USDT Spot pair used only to prioritize that pair in Dashboard selection. It is not ownership, a portfolio holding, or an Auto Trading setting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer following project docs can run the app locally and open Dashboard market data with no XT credentials in under 15 minutes (tools already installed).
- **SC-002**: On a successful XT response path, Dashboard shows the selected pair, a genuine latest price, XT as source, and last-update time when available within 5 seconds of a completed refresh for local use. An explicit refresh control is available.
- **SC-003**: When XT provides 24h statistics, at least 90% of visible stat fields on Dashboard map to values present in the XT payload (no invented fillers).
- **SC-004**: For a supported pair with available history, a simple historical presentation is visible after one user navigation/refresh action without leaving Dashboard, and the user can switch among 15m, 1h, 4h, and 1d intervals with the default starting at 1h.
- **SC-005**: In forced failure/unsupported/malformed cases, 100% of observed outcomes show a clear non-success status and 0 fabricated prices/candles.
- **SC-006**: On ~375px width, pair selection/view, price or error status, and source/status remain completable/readable without desktop-only controls.
- **SC-007**: Code review / architecture check confirms XT-specific calls are confined behind the exchange/market-data adapter boundary (no direct XT coupling in Dashboard presentation logic).
- **SC-009**: After favoriting a supported USDT Spot pair, a Dashboard reload on the same local device still shows that pair in the favorites section before the full searchable list, without creating portfolio or Auto Trading state.

## Assumptions

- “Supported pair” means a Spot symbol XT currently lists via its public market-data surface used by this feature **and** whose quote currency is USDT.
- Default selected pair on first Dashboard load (no valid local persistence) is a widely traded Spot USDT pair when available (prefer BTC paired with USDT if present); otherwise the first available supported USDT pair; if none, show empty/unavailable status.
- Last selected pair and historical interval are persisted on the local device across reloads (FR-018). Persistence does not require user accounts or server-side preference storage.
- Pair favorites are stored on the local device only (FR-019). Favorites are a Dashboard selection aid; they do not use accounts, database persistence, portfolio behavior, or trading behavior.
- Pair selection for Feature 002 offers USDT-quoted Spot pairs only; expanding to other quote currencies is out of scope.
- Historical presentation supports exactly four user-selectable intervals: 15 minutes, 1 hour, 4 hours, and 1 day. Default active interval is 1 hour.
- “Stale” means market data older than a documented freshness threshold suitable for REST polling (default: 60 seconds since last successful observation unless planning sets another value). Stale data MUST be labeled STALE; last known values MAY remain visible but MUST NOT be silently treated as fresh.
- Users MUST be able to refresh market data explicitly (FR-017). Light automatic refresh (about every 30–60 seconds) MAY be implemented but is not required for acceptance.
- Feature 001 shell (three primary areas, health, routing) remains the host application; this feature extends Dashboard content only.
- No user accounts or authentication are introduced.
- Constitution stack and adapter isolation apply at planning/implementation; functional requirements stay outcome-focused.
- Market Sentiment (constitution) remains a future Dashboard capability and is explicitly out of scope here.
- Public XT rate limits and occasional outages are expected; fail-safe UX is part of success, not a defect if XT is down.
