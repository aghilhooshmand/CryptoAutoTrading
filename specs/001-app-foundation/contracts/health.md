# Contract: Backend Health

**Feature**: `001-app-foundation`  
**Date**: 2026-08-08  
**Consumer**: Developers, automated tests, and optionally the frontend

## `GET /health`

Returns whether the backend application process is running correctly.

### Request

- Method: `GET`
- Path: `/health`
- Auth: none
- Body: none

### Successful response (backend up)

- HTTP status: `200`
- Content-Type: `application/json`

```json
{
  "status": "healthy"
}
```

Optional additional fields (`service`, `checkedAt`) are allowed but not
required for acceptance.

### Failure / unavailable

When the backend is not running or not reachable:

- The client MUST observe connection failure or a non-success outcome.
- The system MUST NOT present a successful `status: "healthy"` response from a
  living backend process that is intentionally stopped (i.e., stopped process →
  no healthy success).

Detailed dependency diagnostics (database, exchange, etc.) are **out of scope**
for this contract.

### Acceptance mapping

| Spec | Contract behavior |
|------|-------------------|
| FR-007 / SC-004 | `200` + `status: "healthy"` while backend is up; local successful check completes in under 2 seconds |
| FR-008 / SC-005 | Stopped backend → check does not succeed as healthy (documented manual acceptance check for Feature 001) |

### Non-goals

- Liveness vs readiness split
- Authenticated health
- Aggregating external service health
- Frontend-only mock of healthy status
- Dashboard health widget (not required for Feature 001)
