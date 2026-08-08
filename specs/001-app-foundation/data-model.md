# Data Model: Application Foundation

**Feature**: `001-app-foundation`  
**Date**: 2026-08-08

This feature introduces **no persisted domain database**. Entities below are
runtime/UI concepts used for navigation and health verification.

## Primary Area

Represents one of the three constitution-mandated product destinations.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | enum string | Stable identifier | MUST be one of `dashboard`, `auto-trading`, `portfolio` |
| `label` | string | User-visible name | MUST be exactly `Dashboard`, `Auto Trading`, or `Portfolio` matching `id` |
| `path` | string | Client route path | MUST be unique; recommended `/`, `/auto-trading`, `/portfolio` (or `/dashboard` aliased to default) |
| `isDefaultEntry` | boolean | Whether this area is the default entry | Exactly one Primary Area MUST have `true` — **Dashboard** |
| `contentMode` | enum | Presentation mode | MUST be `placeholder` for this feature |

### Relationships

- The application shell has exactly three Primary Area instances.
- Primary navigation enumerates all three; unknown paths are **not** Primary Areas.

### State transitions

None. Areas are static destinations in this feature; selection changes active
view only (no server-side session).

## Backend Health Status

Concise readiness signal for the backend application process.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `status` | enum string | Readiness | When reachable and healthy: MUST be `healthy` (or equivalent documented success token). MUST NOT claim healthy when process is down. |
| `service` | string | Optional service name | If present, identifies the backend (e.g., `cryptoautotrading-api`) |
| `checkedAt` | datetime string | Optional timestamp | Informative only; not required for acceptance |

### Relationships

- Independent of Primary Areas. Frontend navigation MUST work even when Health
  Status is unreachable.
- No dependency on databases, exchanges, or market feeds in this feature.

### State transitions

| From | To | Trigger |
|------|----|---------|
| unreachable | healthy | Backend process started and responding |
| healthy | unreachable | Backend process stopped or network failure |

No degraded/partial states in this feature (binary readiness per spec assumptions).

## Out of model (explicit)

Do **not** model for this feature: trades, positions, balances, strategies,
sessions, risk limits, sentiment readings, news items, users, credentials, or
exchange accounts.
