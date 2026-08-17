"""Real execution adapter (Feature 015) — XT market place + reconcile."""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any, Callable, Protocol

from app.execution.port import ExecutionIntent, FillResult
from app.simulation.accounting import FillQuote
from app.simulation.control import reasons as risk_reasons
from app.simulation.money import as_str, d, quantize_money
from app.simulation.position_sizing import intended_notional, is_dust
from app.simulation.real_gates import REAL_ALLOCATED_CAP
from app.xt_account.client import XtPrivateClient
from app.xt_account.credentials import PrivateCredentials, load_credentials
from app.xt_account.errors import (
    CREDENTIALS_MISSING,
    RATE_LIMITED,
    TIMESTAMP_INVALID,
    XT_PRIVATE_UNAVAILABLE,
    XtPrivateError,
)
from app.xt_account.normalize import normalize_order

REAL_EXECUTION_UNAVAILABLE = "real_execution_unavailable"
POLL_BUDGET_SECONDS = 5.0

_FILLED_STATES = frozenset({"FILLED", "filled", "COMPLETED", "completed", "SUCCESS", "success"})
_PARTIAL_STATES = frozenset({"PARTIALLY_FILLED", "partially_filled", "PARTIAL", "partial"})
_REJECTED_STATES = frozenset({"REJECTED", "rejected", "CANCELED", "canceled", "CANCELLED", "cancelled", "FAILED", "failed"})


class RealXtClient(Protocol):
    async def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str | None = None,
        quote_qty: str | None = None,
    ) -> Any: ...

    async def get_order(self, order_id: str) -> Any: ...

    async def aclose(self) -> None: ...


# Tests inject fake client factory: () -> RealXtClient
_client_factory_override: Callable[[PrivateCredentials], RealXtClient] | None = None


def set_client_factory_override(
    factory: Callable[[PrivateCredentials], RealXtClient] | None,
) -> None:
    global _client_factory_override
    _client_factory_override = factory


def _client_for(credentials: PrivateCredentials) -> RealXtClient:
    if _client_factory_override is not None:
        return _client_factory_override(credentials)
    return XtPrivateClient(credentials)


def _fill_from_private_error(
    exc: XtPrivateError,
    *,
    xt_order_id: str | None = None,
) -> FillResult:
    if exc.code == CREDENTIALS_MISSING:
        code = risk_reasons.CREDENTIALS_MISSING
    elif exc.code in (RATE_LIMITED, TIMESTAMP_INVALID, XT_PRIVATE_UNAVAILABLE):
        code = exc.code
    else:
        code = risk_reasons.XT_ORDER_REJECTED
    blocked = xt_order_id is not None
    return FillResult(
        False,
        code,
        str(exc),
        xt_order_id=xt_order_id,
        reconcile_status="unsettled" if blocked else None,
        blocked=blocked,
    )


def _extract_order_id(place_result: Any) -> str | None:
    if isinstance(place_result, dict):
        for key in ("orderId", "order_id", "id"):
            val = place_result.get(key)
            if val is not None and str(val) != "":
                return str(val)
    return None


def _order_state(raw: Any) -> tuple[str | None, str | None, str | None]:
    order = normalize_order(raw if isinstance(raw, dict) else raw)
    if order is None:
        return None, None, None
    return order.status, order.executedQty, order.price


def _filled_qty_and_price(
    executed_qty: str | None,
    price: str | None,
    reference: Decimal,
) -> tuple[Decimal, Decimal] | None:
    if executed_qty is None:
        return None
    try:
        qty = d(executed_qty)
    except Exception:  # noqa: BLE001
        return None
    if qty <= 0:
        return None
    fill_price = d(price) if price else reference
    return qty, fill_price


def _fill_quote_from_xt(
    *,
    side: str,
    qty: Decimal,
    reference: Decimal,
    fill_price: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> FillQuote:
    if side == "BUY":
        notional = quantize_money(qty * fill_price)
        fee = quantize_money(notional * fee_rate)
        slippage_cost = quantize_money((fill_price - reference) * qty)
        cash_delta = quantize_money(-(notional + fee))
        return FillQuote(reference, fill_price, notional, fee, slippage_cost, cash_delta)
    notional = quantize_money(qty * fill_price)
    fee = quantize_money(notional * fee_rate)
    slippage_cost = quantize_money((reference - fill_price) * qty)
    cash_delta = quantize_money(notional - fee)
    return FillQuote(reference, fill_price, notional, fee, slippage_cost, cash_delta)


class RealExecutionAdapter:
    """Controlled Real adapter — sole intended XT write path from approved intents."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    def execute(self, intent: ExecutionIntent) -> FillResult:
        if intent.side not in ("BUY", "SELL"):
            return FillResult(False, "invalid_side", "side must be BUY or SELL")
        if (intent.order_type or "MARKET").upper() != "MARKET":
            return FillResult(
                False,
                risk_reasons.LIMIT_ORDERS_UNAVAILABLE,
                risk_reasons.message_for(risk_reasons.LIMIT_ORDERS_UNAVAILABLE),
            )
        if intent.allocated_capital > REAL_ALLOCATED_CAP:
            return FillResult(
                False,
                risk_reasons.REAL_CAPITAL_CAP_EXCEEDED,
                risk_reasons.message_for(risk_reasons.REAL_CAPITAL_CAP_EXCEEDED),
            )
        try:
            credentials = load_credentials()
        except XtPrivateError as exc:
            if exc.code == CREDENTIALS_MISSING:
                return FillResult(
                    False,
                    risk_reasons.CREDENTIALS_MISSING,
                    risk_reasons.message_for(risk_reasons.CREDENTIALS_MISSING),
                )
            return FillResult(False, REAL_EXECUTION_UNAVAILABLE, str(exc))

        if not self._enabled:
            return FillResult(
                False,
                REAL_EXECUTION_UNAVAILABLE,
                "Real execution adapter is disabled",
            )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._execute_async(intent, credentials))
        # Called from async context — run in a thread would be ideal; for MVP use new loop in thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(self._execute_async(intent, credentials))).result()

    async def _execute_async(
        self,
        intent: ExecutionIntent,
        credentials: PrivateCredentials,
    ) -> FillResult:
        client = _client_for(credentials)
        try:
            if intent.side == "BUY":
                return await self._buy(client, intent)
            return await self._sell(client, intent)
        finally:
            await client.aclose()

    async def _buy(self, client: RealXtClient, intent: ExecutionIntent) -> FillResult:
        if intent.position_side != "flat":
            return FillResult(False, "conflicting_position_state", "BUY only from flat")
        target = intended_notional(
            intent.cash,
            intent.fee_rate,
            intent.allocated_capital,
            intent.max_position_size,
        )
        if target > REAL_ALLOCATED_CAP:
            return FillResult(
                False,
                risk_reasons.REAL_CAPITAL_CAP_EXCEEDED,
                risk_reasons.message_for(risk_reasons.REAL_CAPITAL_CAP_EXCEEDED),
            )
        if is_dust(target):
            return FillResult(False, "insufficient_balance", "Intended notional is dust or zero")
        quote_qty = as_str(target)
        return await self._place_and_reconcile(
            client,
            intent,
            side="BUY",
            quantity=None,
            quote_qty=quote_qty,
            expected_full_qty=None,
        )

    async def _sell(self, client: RealXtClient, intent: ExecutionIntent) -> FillResult:
        if intent.position_side != "long" or intent.position_qty <= 0:
            return FillResult(False, "conflicting_position_state", "SELL only while long")
        qty = as_str(intent.position_qty)
        return await self._place_and_reconcile(
            client,
            intent,
            side="SELL",
            quantity=qty,
            quote_qty=None,
            expected_full_qty=intent.position_qty,
        )

    async def _place_and_reconcile(
        self,
        client: RealXtClient,
        intent: ExecutionIntent,
        *,
        side: str,
        quantity: str | None,
        quote_qty: str | None,
        expected_full_qty: Decimal | None,
    ) -> FillResult:
        deadline = time.monotonic() + POLL_BUDGET_SECONDS
        xt_order_id: str | None = None
        try:
            place_result = await client.place_market_order(
                symbol=intent.symbol,
                side=side,
                quantity=quantity,
                quote_qty=quote_qty,
            )
            xt_order_id = _extract_order_id(place_result)
        except XtPrivateError as exc:
            return _fill_from_private_error(exc)

        if xt_order_id is None:
            return FillResult(
                False,
                risk_reasons.XT_RECONCILE_UNSETTLED,
                "XT accepted place without order id; outcome unsettled",
            )

        last_status: str | None = None
        last_executed: str | None = None
        last_price: str | None = None

        while time.monotonic() < deadline:
            try:
                raw = await client.get_order(xt_order_id)
            except XtPrivateError:
                await asyncio.sleep(0.2)
                continue
            last_status, last_executed, last_price = _order_state(raw)
            if last_status in _REJECTED_STATES:
                return FillResult(
                    False,
                    risk_reasons.XT_ORDER_REJECTED,
                    f"XT order {xt_order_id} rejected ({last_status})",
                )
            parsed = _filled_qty_and_price(last_executed, last_price, intent.reference_price)
            if parsed is None:
                await asyncio.sleep(0.2)
                continue
            filled_qty, fill_price = parsed
            fill = _fill_quote_from_xt(
                side=side,
                qty=filled_qty,
                reference=intent.reference_price,
                fill_price=fill_price,
                fee_rate=intent.fee_rate,
                slippage_rate=intent.slippage_rate,
            )
            is_full = last_status in _FILLED_STATES
            if expected_full_qty is not None and filled_qty + Decimal("0.00000001") < expected_full_qty:
                is_full = False
            if is_full or (side == "BUY" and last_status in _FILLED_STATES):
                return FillResult(
                    True,
                    qty=filled_qty,
                    fill=fill,
                    xt_order_id=xt_order_id,
                    reconcile_status="filled",
                )
            if last_status in _PARTIAL_STATES or (
                expected_full_qty is not None and filled_qty < expected_full_qty
            ):
                return FillResult(
                    False,
                    risk_reasons.PARTIAL_FILLED_BLOCKED,
                    risk_reasons.message_for(risk_reasons.PARTIAL_FILLED_BLOCKED),
                    fill=fill,
                    qty=filled_qty,
                    xt_order_id=xt_order_id,
                    reconcile_status="partial_filled_blocked",
                    blocked=True,
                )
            await asyncio.sleep(0.2)

        return FillResult(
            False,
            risk_reasons.XT_RECONCILE_UNSETTLED,
            risk_reasons.message_for(risk_reasons.XT_RECONCILE_UNSETTLED),
            xt_order_id=xt_order_id,
            reconcile_status="unsettled",
            blocked=True,
        )
