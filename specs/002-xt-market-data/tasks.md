# Tasks: XT Spot Market Data

**Input**: Design documents from `/specs/002-xt-market-data/`
     
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included where plan.md requires automated verification (backend market-data contracts + XT adapter unit mapping; frontend prefs/status/race behavior). Chart library may be mocked in frontend tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`
- Frontend: `frontend/src/`
- Docs: `README.md` at repository root; feature docs under `specs/002-xt-market-data/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend Feature 001 packages with market-data directories and dependencies (no feature behavior yet)

- [x] T001 Create backend package dirs `backend/app/market_data/`, `backend/app/market_data/adapters/`, and ensure `backend/tests/contract/` + `backend/tests/unit/` exist per plan.md
- [x] T002 [P] Create frontend dirs `frontend/src/features/market-data/` and `frontend/src/services/` per plan.md
- [x] T003 [P] Add runtime `httpx` dependency in `backend/pyproject.toml` (keep pytest/httpx dev extras intact)
- [x] T004 [P] Add `lightweight-charts` dependency in `frontend/package.json`
- [x] T005 Extend Vite proxy in `frontend/vite.config.ts` to forward `/market` (and keep `/health`) to `http://127.0.0.1:8000`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Adapter boundary, internal models, service/router wiring, and typed frontend API client that ALL user stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 [P] Define internal Pydantic models (`TradingPair`, `MarketQuote`, `Candlestick`, `CandlestickSeries`, status enums) with **decimal-string** financial fields and percent-point `changePercent` in `backend/app/market_data/models.py` per data-model.md
- [x] T007 [P] Define `MarketDataAdapter` protocol in `backend/app/market_data/adapters/base.py`
- [x] T008 Implement `XtSpotAdapter` in `backend/app/market_data/adapters/xt_spot.py` calling only public `https://sapi.xt.com` endpoints (`/v4/public/symbol`, `/ticker`, `/kline`), normalizing envelopes to internal models (convert XT `cr` ratio → percent-point decimal string; no credentials)
- [x] T009 Implement market-data service orchestration in `backend/app/market_data/service.py` over the adapter (USDT filter, default-pair helpers, typed failures)
- [x] T010 Create FastAPI routes `GET /market/pairs`, `GET /market/quote`, `GET /market/candles` in `backend/app/api/market_data.py` per `specs/002-xt-market-data/contracts/market-data.md`
- [x] T011 Mount market-data router in `backend/app/main.py` without breaking `GET /health`
- [x] T012 [P] Add package markers `backend/app/market_data/__init__.py` and `backend/app/market_data/adapters/__init__.py`
- [x] T013 [P] Create typed frontend client `frontend/src/services/marketDataApi.ts` for `/market/pairs|quote|candles` (normalized types only; no XT URLs/keys)
- [x] T014 [P] Create Dashboard prefs helpers (last symbol, last interval default `1h`, favorites) in `frontend/src/features/market-data/prefs.ts` using `localStorage` only

**Checkpoint**: Foundation ready — backend `/market/*` callable; frontend can call contracts; XT isolated in adapter

---

## Phase 3: User Story 1 - View genuine XT Spot market data on the Dashboard (Priority: P1) 🎯 MVP

**Goal**: Dashboard shows real XT-sourced pair identity, latest price, available 24h stats, XT source label, last-update time, and a working manual Refresh control (no credentials).

**Independent Test**: Run app locally without XT keys; open Dashboard; confirm genuine price/source/update time; trigger Refresh and see update or clear failure—never fabricated values.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US1] Add contract tests for `GET /market/quote` (decimal-string fields, `changePercent` percent points, `source: XT`, error/unsupported paths) in `backend/tests/contract/test_market_data.py`
- [x] T016 [P] [US1] Add unit tests for XT ticker→`MarketQuote` mapping (including `cr` → percent points) in `backend/tests/unit/test_xt_spot_adapter.py`

### Implementation for User Story 1

- [x] T017 [US1] Implement quote panel UI (price, available 24h stats, XT source, last update) in `frontend/src/features/market-data/MarketQuotePanel.tsx`
- [x] T018 [US1] Implement status badge component in `frontend/src/features/market-data/MarketStatusBadge.tsx` (at least loading/fresh/error/unavailable for MVP; STALE refined in US4)
- [x] T019 [US1] Implement `useMarketData` fetch + **manual refresh** + request-generation race guard in `frontend/src/features/market-data/useMarketData.ts` (auto-refresh NOT required)
- [x] T020 [US1] Compose market quote + refresh into `frontend/src/pages/DashboardPage.tsx`, replacing Feature 001 placeholder-only market messaging for this scope
- [x] T021 [US1] Run backend tests for T015–T016 and fix until passing; smoke `curl` quote path from quickstart.md; verify SC-002’s **5-second** Dashboard update bound after a completed refresh during the **manual** acceptance check unless already covered automatically

**Checkpoint**: MVP — Dashboard shows genuine XT quote with manual refresh

---

## Phase 4: User Story 2 - Select a supported XT Spot trading pair (Priority: P1)

**Goal**: Searchable USDT-only pair selector; local favorites above the full list; persist last selected pair; favorites do not imply portfolio/Auto Trading state.

**Independent Test**: Search/select another USDT pair; confirm quote updates (or clear loading/error); favorite persists across reload; Auto Trading/Portfolio unchanged placeholders.

### Tests for User Story 2

- [x] T022 [P] [US2] Extend `backend/tests/contract/test_market_data.py` for `GET /market/pairs` (USDT-only symbols, failure → no invented pairs)
- [x] T023 [P] [US2] Add frontend tests for prefs restore + favorites ordering in `frontend/src/__tests__/marketPrefs.test.tsx` (or under `frontend/src/features/market-data/`)

### Implementation for User Story 2

- [x] T024 [US2] Implement searchable pair selector with favorites section-before-list in `frontend/src/features/market-data/PairSelector.tsx`
- [x] T025 [US2] Wire pair list load, selection, favorite/unfavorite, and last-symbol persistence via `prefs.ts` + `useMarketData.ts` + `DashboardPage.tsx`
- [x] T026 [US2] Enforce default pair rules (`btc_usdt` if available, else first USDT pair, else empty/unavailable) and drop unsupported persisted/favorite symbols without fabricating prices
- [x] T027 [US2] Confirm `frontend/src/pages/AutoTradingPage.tsx` and `frontend/src/pages/PortfolioPage.tsx` remain placeholders with no favorite-driven portfolio/trading state
- [x] T028 [US2] Run tests for T022–T023 and fix until passing

**Checkpoint**: Pair selection + local favorites/persistence work on Dashboard only

---

## Phase 5: User Story 4 - Stay safe when XT data fails or is stale (Priority: P1)

**Goal**: Fail-safe statuses; quote-based STALE after 60s (`observedAt` else `retrievedAt`); last-known values may remain with explicit STALE; never present stale as fresh; health ≠ market status.

**Independent Test**: Force failure/malformed/unsupported; confirm clear non-success and zero fabricated prices; age a quote >60s and confirm STALE labeling; navigate primary areas still works.

### Tests for User Story 4

- [x] T029 [P] [US4] Add/extend adapter unit tests for malformed XT payloads and missing critical fields in `backend/tests/unit/test_xt_spot_adapter.py`
- [x] T030 [P] [US4] Add frontend tests that STALE uses quote timestamps (not candle `openTime`) and does not label stale as fresh in `frontend/src/__tests__/marketStatus.test.tsx`

### Implementation for User Story 4

- [x] T031 [US4] Complete fail-safe mapping in `backend/app/market_data/service.py` and `backend/app/api/market_data.py` (`unsupported`/`unavailable`/`error` HTTP + bodies per contracts; no fabricated values)
- [x] T032 [US4] Implement client-side quote freshness (60s from `observedAt` else `retrievedAt`) and STALE display in `MarketStatusBadge.tsx` / `MarketQuotePanel.tsx` / `useMarketData.ts`
- [x] T033 [US4] Ensure race guard ignores stale responses so older pair/interval results cannot overwrite newer selection in `useMarketData.ts`
- [x] T034 [US4] Keep `GET /health` behavior unchanged in `backend/app/api/health.py` and ensure Dashboard distinguishes process health from market-data status where both are observable
- [x] T035 [US4] Run tests for T029–T030 and fix until passing

**Checkpoint**: Fail-safe + quote-based STALE meet FR-008/FR-009 / SC-005

---

## Phase 6: User Story 3 - View historical candlestick/price history (Priority: P2)

**Goal**: Simple candlestick/history for intervals `15m`/`1h`/`4h`/`1d` (default `1h`); persist last interval; never invent candles; candle `openTime` does not drive Dashboard STALE.

**Independent Test**: With a supported pair, view history; switch intervals; confirm reload restores interval; on history failure show clear empty/error without fake candles.

### Tests for User Story 3

- [x] T036 [P] [US3] Extend `backend/tests/contract/test_market_data.py` for `GET /market/candles` (allowed intervals only, decimal-string OHLC, invalid interval → 400)
- [x] T037 [P] [US3] Extend `backend/tests/unit/test_xt_spot_adapter.py` for kline → `CandlestickSeries` mapping

### Implementation for User Story 3

- [x] T038 [US3] Implement candle chart component using `lightweight-charts` in `frontend/src/features/market-data/CandleChart.tsx` (consume normalized series only; mockable in tests)
- [x] T039 [US3] Add interval control (`15m`/`1h`/`4h`/`1d`, default `1h`) and wire candles fetch + last-interval persistence in `useMarketData.ts`, `prefs.ts`, and `DashboardPage.tsx`
- [x] T040 [US3] On history failure/empty, show clear unavailable/error empty state in `CandleChart.tsx` / Dashboard without padding fake candles
- [x] T041 [US3] Run tests for T036–T037 and fix until passing

**Checkpoint**: History + intervals work; STALE remains quote-based

---

## Phase 7: User Story 5 - Use market data on phone-width screens (Priority: P2)

**Goal**: At ~375px, pair selection, price or error status, source/status, refresh, and simple history remain usable/readable.

**Independent Test**: Resize to ~375px; complete pair view + status readability for Dashboard market-data section without desktop-only gestures.

### Tests for User Story 5

- [x] T042 [P] [US5] Add/extend narrow-viewport smoke assertions for Dashboard market controls in `frontend/src/__tests__/marketResponsive.test.tsx` (or extend existing responsive tests)

### Implementation for User Story 5

- [x] T043 [US5] Adjust styles/layout in `frontend/src/features/market-data/*.tsx` and `frontend/src/pages/DashboardPage.tsx` so market UI is usable at ~375px
- [x] T044 [US5] Manually verify quickstart phone-width scenario; fix clipping/overflow in the same feature files
- [x] T045 [US5] Run frontend tests including T042 and fix until passing

**Checkpoint**: Phone-width market Dashboard satisfies SC-006 / FR-012

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Docs, acceptance validation, adapter isolation check; auto-refresh only if trivial

- [x] T046 [P] Update root `README.md` with Feature 002 market-data run notes (no XT credentials; `/market` proxy; manual refresh) linking to `specs/002-xt-market-data/quickstart.md`
- [x] T047 [P] Confirm frontend has no `sapi.xt.com` / XT short-key coupling (search `frontend/src/`); XT calls only under `backend/app/market_data/adapters/`
- [x] T048 Run full quickstart.md validation scenarios (pairs, quote, candles, STALE, race, out-of-scope) and fix gaps in the touched app files
- [x] T049 [P] Optional polish ONLY: light ~60s auto-refresh for active pair in `useMarketData.ts` if trivial and rate-limit-safe — **MUST NOT block Feature 002 completion** if skipped — **skipped** (manual refresh only; keeps rate-limit posture simple)
- [x] T050 Confirm out-of-scope remains unimplemented (no trading/simulation/risk/strategies/portfolio math/sentiment/news/auth/WebSockets/SQL prefs/futures/margin/leverage) per SC-008

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — MVP
- **User Story 2 (Phase 4)**: After Foundational; practically after US1 quote panel exists for selection to update visible data
- **User Story 4 (Phase 5)**: After Foundational; builds on US1 status/quote display (and benefits from US2 selection)
- **User Story 3 (Phase 6)**: After Foundational; integrates with selected pair/interval from US2 prefs
- **User Story 5 (Phase 7)**: After market UI from US1–US4/US3 exists to style
- **Polish (Phase 8)**: After desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Foundation only — MVP quote + refresh
- **US2 (P1)**: Foundation; uses `/market/pairs` + prefs; integrates with US1 Dashboard
- **US4 (P1)**: Hardens US1/US2 fail-safe + STALE; independently testable with forced failures
- **US3 (P2)**: Foundation + selected symbol/interval; chart independent of favorites
- **US5 (P2)**: Responsive pass over Dashboard market UI

### Within Each User Story

- Tests (where listed) SHOULD be written and fail before implementation
- Models/adapter already in Foundation; story work focuses on contracts UI + wiring
- Manual refresh required before any optional auto-refresh polish

### Parallel Opportunities

- Phase 1: T002, T003, T004 in parallel after/with T001
- Phase 2: T006∥T007; T012∥T013∥T014 after models/adapter direction clear; T008→T009→T010→T011 sequential
- US1: T015∥T016; then UI T017∥T018 before T019–T020
- US2: T022∥T023; T024 then T025–T027
- US4: T029∥T030
- US3: T036∥T037; T038 then T039–T040
- Polish: T046∥T047∥T049 (T049 optional)

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Contract tests for GET /market/quote in backend/tests/contract/test_market_data.py"
Task: "Unit tests for XT ticker mapping in backend/tests/unit/test_xt_spot_adapter.py"

# UI pieces in parallel after hook/API client exists:
Task: "MarketQuotePanel in frontend/src/features/market-data/MarketQuotePanel.tsx"
Task: "MarketStatusBadge in frontend/src/features/market-data/MarketStatusBadge.tsx"
```

---

## Parallel Example: User Story 2

```bash
Task: "Contract tests for GET /market/pairs in backend/tests/contract/test_market_data.py"
Task: "Prefs/favorites tests in frontend/src/__tests__/marketPrefs.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (quote + manual refresh on Dashboard)
4. **STOP and VALIDATE** against quickstart Scenario 1
5. Demo MVP without pair search/favorites/chart if needed

### Incremental Delivery

1. Setup + Foundational → `/market` contracts live
2. US1 → genuine XT quote on Dashboard (MVP)
3. US2 → searchable USDT pairs + favorites + last pair
4. US4 → STALE + fail-safe hardening
5. US3 → candles + intervals
6. US5 → phone-width polish
7. Phase 8 docs/validation; skip T049 unless trivial

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Dev A: US1 → US4
   - Dev B: US2 (pairs/favorites) then help US3 chart
   - Dev C: US3 candles contract/adapter tests + chart
3. US5 + Polish after UI surfaces exist

---

## Notes

- [P] = different files, no incomplete-task dependencies
- Financial API fields MUST be decimal strings; `changePercent` is percent points (`"2.35"` = +2.35%)
- Dashboard STALE is quote-timed only — never candle `openTime`
- Auto-refresh (T049) is optional polish and must not block completion
- No XT credentials, private APIs, WebSockets, trading, sentiment, portfolio math, or SQL prefs
- Propose Git commits; do not auto-commit (Constitution XXX)
- Stop at checkpoints to validate each story independently
