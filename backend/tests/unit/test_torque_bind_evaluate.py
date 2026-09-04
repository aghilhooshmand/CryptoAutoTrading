"""evaluate_phenotype envelope + import guards (Feature 016 US3)."""

from __future__ import annotations

import ast
from pathlib import Path

from app.market_data.models import Candlestick
from app.torque_bind import evaluate_phenotype
from app.torque_bind.bind import ensure_strategies_registered


def _candles(n: int = 50) -> list[Candlestick]:
    out = []
    px = 100.0
    start = 1_700_000_000_000
    step = 3_600_000
    for i in range(n):
        px += 0.4 if i < 30 else -0.6
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=str(px),
                high=str(px + 1),
                low=str(px - 1),
                close=str(px),
            )
        )
    return out


def test_evaluate_phenotype_success_shape():
    ensure_strategies_registered()
    out = evaluate_phenotype(
        "rsi(period=14, oversold=30, overbought=70)",
        candles=_candles(),
        starting_capital="1000",
    )
    assert out["ok"] is True
    assert "netProfit" in out["metrics"]
    assert "effectiveLeaves" in out
    assert out["effectiveLeaves"][0]["strategyId"] == "rsi"
    assert out["metrics"]["tradeCount"] is not None


def test_evaluate_phenotype_fail_closed_unknown_leaf():
    out = evaluate_phenotype("foo(period=14)", candles=_candles())
    assert out["ok"] is False
    assert out["error"]["code"] == "unknown_torque_leaf"


def test_evaluate_phenotype_fail_closed_bad_form():
    out = evaluate_phenotype("!!!", candles=_candles())
    assert out["ok"] is False
    assert out["error"]["code"] == "invalid_torque_form"


def _module_imports_forbidden(path: Path, forbidden_substrings: list[str]) -> list[str]:
    """Return forbidden import hits found via AST (no execution)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for bad in forbidden_substrings:
                    if bad in alias.name:
                        hits.append(f"{path.name}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            for bad in forbidden_substrings:
                if bad in node.module:
                    hits.append(f"{path.name}: from {node.module}")
    return hits


def test_torque_bind_does_not_import_real_place_path():
    root = Path(__file__).resolve().parents[2] / "app" / "torque_bind"
    hits: list[str] = []
    for path in root.glob("*.py"):
        hits.extend(
            _module_imports_forbidden(
                path,
                [
                    "app.execution.real",
                    "app.adapters.kraken.private",
                    "RealExecutionAdapter",
                ],
            )
        )
    assert hits == []


def test_core_modules_do_not_import_forge_torque():
    """Strategy / Controller / Risk must not import FORGE (bind is the boundary)."""
    backend = Path(__file__).resolve().parents[2]
    paths = [
        backend / "app" / "strategy" / "rsi.py",
        backend / "app" / "simulation" / "control" / "controller.py",
        backend / "app" / "simulation" / "control" / "risk.py",
    ]
    hits: list[str] = []
    for path in paths:
        hits.extend(_module_imports_forbidden(path, ["torque", "forge", "uge"]))
    assert hits == []
