"""Strategy/Controller/Risk must stay venue-adapter-free (FR-028 / FR-032)."""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2] / "app"
_SCAN = [
    _ROOT / "strategy",
    _ROOT / "simulation" / "control",
]


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_strategy_controller_risk_do_not_import_venue_adapters() -> None:
    forbidden = (
        "app.market_data.adapters",
        "app.market_data.adapters.kraken_public",
        "app.market_data.adapters.xt_spot",
        "KrakenPublicAdapter",
        "XtSpotAdapter",
    )
    files = [p for folder in _SCAN for p in folder.rglob("*.py")]
    assert files
    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        imported = _imported_modules(path)
        if any(name.startswith("app.market_data.adapters") for name in imported):
            offenders.append(str(path))
            continue
        if any(token in text for token in forbidden[3:]):
            offenders.append(str(path))
    assert offenders == []
