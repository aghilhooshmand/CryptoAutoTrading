"""Fitness evaluator + import guards (Feature 019)."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from app.market_data.models import Candlestick
from app.torque_bind.bind import ensure_strategies_registered
from app.uge_search.fitness import make_backtest_evaluator, score_phenotype


def _candles(n: int = 50) -> list[Candlestick]:
    out = []
    start = 1_700_000_000_000
    step = 3_600_000
    px_cents = 10000
    for i in range(n):
        px_cents += 50 if i < 25 else -40
        px = f"{px_cents / 100:.2f}"
        out.append(
            Candlestick(
                openTime=start + i * step,
                open=px,
                high=f"{(px_cents + 50) / 100:.2f}",
                low=f"{(px_cents - 50) / 100:.2f}",
                close=px,
            )
        )
    return out


def test_evaluator_success_and_fail_closed():
    ensure_strategies_registered()
    candles = _candles()
    evaluate = make_backtest_evaluator(candles, fitness_id="net_minus_bh")
    ok_ind = SimpleNamespace(
        mapping=SimpleNamespace(invalid=False, phenotype="rsi(period=14, oversold=30, overbought=70)")
    )
    bad_ind = SimpleNamespace(mapping=SimpleNamespace(invalid=False, phenotype="not_a_program!!!"))
    invalid_map = SimpleNamespace(mapping=SimpleNamespace(invalid=True, phenotype=""))
    r_ok = evaluate(ok_ind)
    assert r_ok.ok and r_ok.fitness is not None
    assert evaluate(bad_ind).ok is False
    assert evaluate(invalid_map).ok is False


def test_score_phenotype_matches_evaluator_scalar():
    ensure_strategies_registered()
    candles = _candles()
    ph = "rsi(period=14, oversold=30, overbought=70)"
    score = score_phenotype(ph, candles, fitness_id="net_minus_bh")
    assert score is not None
    evaluate = make_backtest_evaluator(candles, fitness_id="net_minus_bh")
    ind = SimpleNamespace(mapping=SimpleNamespace(invalid=False, phenotype=ph))
    r = evaluate(ind)
    assert r.ok
    assert abs(float(r.fitness.objectives[0]) - score) < 1e-9


def _forbidden_imports(path: Path, forbidden: list[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for bad in forbidden:
                    if bad in alias.name:
                        hits.append(f"{path.name}:{alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            for bad in forbidden:
                if bad in node.module:
                    hits.append(f"{path.name}:{node.module}")
    return hits


def test_uge_search_no_real_place_imports():
    root = Path(__file__).resolve().parents[2] / "app" / "uge_search"
    hits: list[str] = []
    for path in root.glob("*.py"):
        hits.extend(
            _forbidden_imports(
                path,
                ["app.execution.real", "RealExecutionAdapter", "force"],
            )
        )
    assert hits == []


def test_core_modules_do_not_import_uge():
    backend = Path(__file__).resolve().parents[2]
    paths = [
        backend / "app" / "strategy" / "rsi.py",
        backend / "app" / "simulation" / "control" / "controller.py",
        backend / "app" / "simulation" / "control" / "risk.py",
    ]
    hits: list[str] = []
    for path in paths:
        hits.extend(_forbidden_imports(path, ["uge"]))
    assert hits == []
