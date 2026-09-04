"""Catalogue allow-lists and error code constants (Feature 016)."""

from __future__ import annotations

from app.torque_bind.bind import ensure_strategies_registered
from app.torque_bind.catalogue import (
    COMPOSITION_OPS,
    MVP_LEAF_IDS,
    is_composition_name,
    mvp_leaf_catalogue,
    normalize_composition_op,
    resolve_leaf_id,
)
from app.torque_bind.errors import ERROR_CODES, INVALID_TORQUE_FORM, TorqueBindError


def test_error_codes_stable():
    assert INVALID_TORQUE_FORM in ERROR_CODES
    assert len(ERROR_CODES) == 5
    err = TorqueBindError(INVALID_TORQUE_FORM, "bad")
    assert err.to_error_dict() == {"code": "invalid_torque_form", "message": "bad"}


def test_composition_ops_and_aliases():
    assert COMPOSITION_OPS == frozenset({"and", "or", "vote"})
    assert normalize_composition_op("And") == "and"
    assert normalize_composition_op("OR") == "or"
    assert is_composition_name("vote")
    assert not is_composition_name("rsi")


def test_mvp_leaf_catalogue_exposes_paramdefs():
    ensure_strategies_registered()
    assert MVP_LEAF_IDS == frozenset({"rsi", "macd", "dual_ema"})
    cat = mvp_leaf_catalogue()
    by_id = {row["strategyId"]: row for row in cat}
    assert set(by_id) == MVP_LEAF_IDS
    rsi_names = {p["name"] for p in by_id["rsi"]["parameters"]}
    assert "period" in rsi_names
    assert "oversold" in rsi_names
    macd_names = {p["name"] for p in by_id["macd"]["parameters"]}
    assert {"fastPeriod", "slowPeriod", "signalPeriod"} <= macd_names
    for p in by_id["rsi"]["parameters"]:
        if p["name"] == "period":
            assert p.get("minimum") is not None


def test_resolve_leaf_case_insensitive():
    ensure_strategies_registered()
    assert resolve_leaf_id("RSI") == "rsi"
    assert resolve_leaf_id("dual_ema") == "dual_ema"
    assert resolve_leaf_id("no_such_strategy") is None
