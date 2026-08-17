"""Feature 013 amendment: no Kraken private types in Strategy/Controller/Risk;
RealExecutionAdapter is not wired to Kraken place/cancel.
"""

from __future__ import annotations

from pathlib import Path

from app.account.kraken_private import KrakenPrivateClient
from app.execution.real import RealExecutionAdapter


ROOT = Path(__file__).resolve().parents[2] / "app"


def _scan(paths: list[Path], needles: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            offenders.append(str(path.relative_to(ROOT.parent)))
    return offenders


def test_strategy_controller_risk_do_not_import_kraken_private() -> None:
    needles = (
        "kraken_private",
        "KrakenPrivateClient",
        "KrakenAccountService",
        "from app.account",
        "import app.account",
    )
    paths = list((ROOT / "strategy").rglob("*.py"))
    paths.extend((ROOT / "simulation" / "control").glob("*.py"))
    offenders = _scan(paths, needles)
    assert offenders == []


def test_kraken_private_client_has_no_place_or_cancel() -> None:
    source = (ROOT / "account" / "kraken_private.py").read_text(encoding="utf-8")
    assert "AddOrder" not in source
    assert "CancelOrder" not in source
    assert "place_order" not in source
    assert not hasattr(KrakenPrivateClient, "place_order")
    assert not hasattr(KrakenPrivateClient, "place_market_order")
    assert not hasattr(KrakenPrivateClient, "cancel_order")


def test_real_execution_adapter_does_not_import_kraken_private() -> None:
    source = (ROOT / "execution" / "real.py").read_text(encoding="utf-8")
    assert "kraken_private" not in source
    assert "app.account" not in source
    assert "AddOrder" not in source
    assert RealExecutionAdapter is not None


def test_public_kraken_adapter_does_not_read_private_keys() -> None:
    source = (ROOT / "market_data" / "adapters" / "kraken_public.py").read_text(
        encoding="utf-8"
    )
    assert "KRAKEN_API_KEY" not in source
    assert "KRAKEN_API_SECRET" not in source
    assert "API-Sign" not in source
