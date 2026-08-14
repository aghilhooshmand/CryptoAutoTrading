"""Unit tests for Feature 010 risk reason catalog."""

from app.simulation.control import reasons as R


def test_code_not_equal_message_for_portfolio_codes():
    codes = [
        R.INSUFFICIENT_PORTFOLIO_AVAILABLE,
        R.ALLOCATION_EXPOSURE_EXCEEDED,
        R.ALLOCATION_RELEASE_BLOCKED,
        R.ALLOCATION_RESIZE_BLOCKED,
        R.PORTFOLIO_MAX_LOSS,
        R.PORTFOLIO_MAX_LOSS_UNCOMPUTABLE,
        R.PER_SYMBOL_EXPOSURE_EXCEEDED,
    ]
    for code in codes:
        msg = R.message_for(code)
        assert msg != code
        assert len(msg) > 0


def test_catalog_includes_legacy_codes():
    assert R.INSUFFICIENT_BALANCE in R.catalog_codes()
    assert R.CONFLICTING_POSITION_STATE in R.catalog_codes()
