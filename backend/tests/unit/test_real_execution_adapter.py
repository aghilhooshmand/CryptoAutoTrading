"""RealExecutionAdapter reconcile behavior with fake XT client (Feature 015 US1)."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.execution.port import ExecutionIntent
from app.execution.real import RealExecutionAdapter, set_client_factory_override


def _order(**fields):
    base = {
        "orderId": "xt-123",
        "symbol": "btc_usdt",
        "side": "BUY",
        "status": "NEW",
        "executedQty": "0",
        "price": "65000",
    }
    base.update(fields)
    return base


class FakeXtClient:
    def __init__(
        self,
        *,
        place_result: dict | None = None,
        order_responses: list[dict] | None = None,
    ) -> None:
        self.place_calls: list[dict] = []
        self.get_calls: list[str] = []
        self._place_result = place_result or {"orderId": "xt-123"}
        self._order_responses = list(order_responses or [])

    async def place_market_order(self, **kwargs):
        self.place_calls.append(kwargs)
        return self._place_result

    async def get_order(self, order_id: str):
        self.get_calls.append(order_id)
        if not self._order_responses:
            return _order()
        return self._order_responses.pop(0)

    async def aclose(self) -> None:
        return None


def _intent(**over) -> ExecutionIntent:
    base = ExecutionIntent(
        side="BUY",
        symbol="btc_usdt",
        reference_price=Decimal("65000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        cash=Decimal("25"),
        allocated_capital=Decimal("25"),
        max_position_size=Decimal("25"),
        position_side="flat",
        position_qty=Decimal("0"),
    )
    for k, v in over.items():
        setattr(base, k, v)
    return base


@pytest.fixture(autouse=True)
def _credentials(monkeypatch):
    monkeypatch.setenv("XT_API_KEY", "test-key")
    monkeypatch.setenv("XT_API_SECRET", "test-secret")
    yield
    set_client_factory_override(None)


def test_place_ack_alone_does_not_fill():
    fake = FakeXtClient(order_responses=[_order(status="NEW", executedQty="0")] * 30)
    set_client_factory_override(lambda _c: fake)

    result = RealExecutionAdapter().execute(_intent())

    assert result.ok is False
    assert result.fill is None
    assert result.qty is None
    assert result.xt_order_id == "xt-123"
    assert result.reconcile_status == "unsettled"
    assert result.blocked is True
    assert result.reason_code == "xt_reconcile_unsettled"
    assert len(fake.place_calls) == 1
    assert len(fake.get_calls) >= 1


def test_filled_only_after_get_order_evidence():
    fake = FakeXtClient(
        order_responses=[
            _order(status="FILLED", executedQty="0.00038461", price="65000"),
        ]
    )
    set_client_factory_override(lambda _c: fake)

    result = RealExecutionAdapter().execute(_intent())

    assert result.ok is True
    assert result.fill is not None
    assert result.qty == Decimal("0.00038461")
    assert result.xt_order_id == "xt-123"
    assert result.reconcile_status == "filled"
    assert fake.get_calls == ["xt-123"]


def test_partial_fill_blocked_with_exposure():
    fake = FakeXtClient(
        order_responses=[
            _order(status="PARTIALLY_FILLED", executedQty="0.0001", price="65000"),
        ]
    )
    set_client_factory_override(lambda _c: fake)

    result = RealExecutionAdapter().execute(_intent())

    assert result.ok is False
    assert result.blocked is True
    assert result.fill is not None
    assert result.qty == Decimal("0.0001")
    assert result.reason_code == "partial_filled_blocked"
    assert result.reconcile_status == "partial_filled_blocked"


def test_xt_reject_does_not_invent_fill():
    from app.xt_account.errors import XT_PRIVATE_UNAVAILABLE, XtPrivateError

    class RejectingClient:
        async def place_market_order(self, **kwargs):
            raise XtPrivateError(XT_PRIVATE_UNAVAILABLE, "XT down")

        async def get_order(self, order_id: str):
            raise AssertionError("get_order must not run after place reject")

        async def aclose(self) -> None:
            return None

    set_client_factory_override(lambda _c: RejectingClient())
    result = RealExecutionAdapter().execute(_intent())
    assert result.ok is False
    assert result.fill is None
    assert result.qty is None
    assert result.xt_order_id is None
    assert result.blocked is False
    assert result.reason_code == "xt_private_unavailable"


def test_limit_orders_unavailable():
    result = RealExecutionAdapter().execute(_intent(order_type="LIMIT"))
    assert result.ok is False
    assert result.fill is None
    assert result.reason_code == "limit_orders_unavailable"

