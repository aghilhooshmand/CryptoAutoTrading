"""Shared Risk / Controller / Execution reason catalog (Feature 010).

Stable ``code`` values are machine identifiers. ``message`` is operator-facing
and may be clarified without renaming codes.
"""

from __future__ import annotations

# Existing Feature 003/004 meanings (retain).
EMERGENCY_STOP_ACTIVE = "emergency_stop_active"
SESSION_NOT_ACTIVE = "session_not_active"
INVALID_OR_STALE_MARKET_DATA = "invalid_or_stale_market_data"
MAXIMUM_TRADES_REACHED = "maximum_trades_reached"
PROFIT_TARGET_ALREADY_REACHED = "profit_target_already_reached"
MAXIMUM_LOSS_ALREADY_REACHED = "maximum_loss_already_reached"
CONFLICTING_POSITION_STATE = "conflicting_position_state"
INSUFFICIENT_BALANCE = "insufficient_balance"
DURATION_ELAPSED = "duration_elapsed"
UNRECOVERABLE_UNSAFE_MARKET_DATA = "unrecoverable_unsafe_market_data"

# Feature 010 portfolio-aware codes.
INSUFFICIENT_PORTFOLIO_AVAILABLE = "insufficient_portfolio_available"
ALLOCATION_EXPOSURE_EXCEEDED = "allocation_exposure_exceeded"
ALLOCATION_RELEASE_BLOCKED = "allocation_release_blocked"
ALLOCATION_RESIZE_BLOCKED = "allocation_resize_blocked"
PORTFOLIO_MAX_LOSS = "portfolio_max_loss"
PORTFOLIO_MAX_LOSS_UNCOMPUTABLE = "portfolio_max_loss_uncomputable"
PER_SYMBOL_EXPOSURE_EXCEEDED = "per_symbol_exposure_exceeded"

# Feature 015 Controlled Real
REAL_CAPITAL_CAP_EXCEEDED = "real_capital_cap_exceeded"
PENDING_CONFIRMATION_EXPIRED = "pending_confirmation_expired"
CONFIRM_VALIDATION_FAILED = "confirm_validation_failed"
LIMIT_ORDERS_UNAVAILABLE = "limit_orders_unavailable"
XT_RECONCILE_UNSETTLED = "xt_reconcile_unsettled"
RESUME_UNAVAILABLE = "resume_unavailable"
NO_PENDING_CONFIRMATION = "no_pending_confirmation"
INSUFFICIENT_XT_FREE = "insufficient_xt_free"
PARTIAL_FILLED_BLOCKED = "partial_filled_blocked"
XT_ORDER_REJECTED = "xt_order_rejected"
CREDENTIALS_MISSING = "credentials_missing"
REAL_RESTART_BLOCKED = "real_restart_blocked"

# Stop trigger aliases (session stop_reason / RiskDecision.trigger_stop).
STOP_MAX_TRADES = "max_trades"
STOP_PROFIT_TARGET = "profit_target"
STOP_MAX_LOSS = "max_loss"
STOP_EMERGENCY = "emergency"
STOP_PORTFOLIO_MAX_LOSS = "portfolio_max_loss"

_MESSAGES: dict[str, str] = {
    EMERGENCY_STOP_ACTIVE: "Emergency stop active",
    SESSION_NOT_ACTIVE: "Session is not active",
    INVALID_OR_STALE_MARKET_DATA: "Mark price unsafe or missing",
    MAXIMUM_TRADES_REACHED: "Max strategy fills reached",
    PROFIT_TARGET_ALREADY_REACHED: "Profit target reached",
    MAXIMUM_LOSS_ALREADY_REACHED: "Max session loss reached",
    CONFLICTING_POSITION_STATE: "Conflicting position state",
    INSUFFICIENT_BALANCE: "Insufficient balance for intended trade",
    DURATION_ELAPSED: "Session duration elapsed",
    UNRECOVERABLE_UNSAFE_MARKET_DATA: "Unrecoverable unsafe market data",
    INSUFFICIENT_PORTFOLIO_AVAILABLE: "Allocated capital exceeds Portfolio available USDT.",
    ALLOCATION_EXPOSURE_EXCEEDED: "Trade would exceed the bound allocation’s reserved size.",
    ALLOCATION_RELEASE_BLOCKED: "Cannot release an allocation while a Simulation is bound to it.",
    ALLOCATION_RESIZE_BLOCKED: "Cannot resize allocation below current deployed exposure.",
    PORTFOLIO_MAX_LOSS: "Portfolio maximum loss bound reached.",
    PORTFOLIO_MAX_LOSS_UNCOMPUTABLE: "Portfolio loss metric cannot be computed; new buys blocked.",
    PER_SYMBOL_EXPOSURE_EXCEEDED: "Trade would exceed the per-symbol weight cap.",
    REAL_CAPITAL_CAP_EXCEEDED: "Real allocated capital exceeds the 50 USDT MVP safety cap.",
    PENDING_CONFIRMATION_EXPIRED: "Pending Real entry confirmation has expired.",
    CONFIRM_VALIDATION_FAILED: "Final pre-submit validation failed; no XT order placed.",
    LIMIT_ORDERS_UNAVAILABLE: "Limit orders are not available for Controlled Real MVP.",
    XT_RECONCILE_UNSETTLED: "XT order outcome unsettled; new orders blocked until reconcile.",
    RESUME_UNAVAILABLE: "Resume unavailable until Real reconciliation proves safe.",
    NO_PENDING_CONFIRMATION: "No pending Real entry confirmation for this session.",
    INSUFFICIENT_XT_FREE: "XT free USDT is insufficient for the intended Real entry.",
    PARTIAL_FILLED_BLOCKED: "Partial XT fill recorded; session blocked until reconcile/Resume.",
    XT_ORDER_REJECTED: "XT rejected the Real order.",
    CREDENTIALS_MISSING: "XT private credentials are not configured.",
    REAL_RESTART_BLOCKED: "Real session blocked after restart; never auto-resumed.",
}


def message_for(code: str, fallback: str | None = None) -> str:
    if code in _MESSAGES:
        return _MESSAGES[code]
    if fallback is not None:
        return fallback
    return code


def catalog_codes() -> frozenset[str]:
    return frozenset(_MESSAGES.keys())
