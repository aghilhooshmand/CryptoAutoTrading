"""RealExecutionAdapter stub — Feature 012 (code/tests only)."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.execution.port import ExecutionIntent
from app.execution.real import REAL_EXECUTION_UNAVAILABLE, RealExecutionAdapter


def _intent() -> ExecutionIntent:
    return ExecutionIntent(
        side="BUY",
        symbol="btc_usdt",
        reference_price=Decimal("100"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        cash=Decimal("25"),
        allocated_capital=Decimal("25"),
        max_position_size=Decimal("25"),
        position_side="flat",
        position_qty=Decimal("0"),
    )


def test_real_stub_structured_unavailable():
    """Scaffold fails closed until US1 enables live place."""
    res = RealExecutionAdapter().execute(_intent())
    assert res.ok is False
    assert res.reason_code in (REAL_EXECUTION_UNAVAILABLE, "credentials_missing")
    assert res.fill is None
    assert res.qty is None


def test_real_stub_does_not_call_portfolio_apply():
    with patch("app.portfolio.service.try_apply_simulation_fill", MagicMock()) as apply:
        RealExecutionAdapter().execute(_intent())
        apply.assert_not_called()


def test_create_apis_have_no_execution_mode_field():
    """Negative check: no separate executionMode field (mode=real on session)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "app" / "api"
    for name in ("simulation.py", "backtest.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "executionMode" not in src
        assert "execution_mode" not in src
