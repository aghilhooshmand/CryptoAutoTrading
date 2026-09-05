"""Load MVP trading BNF for FORGE Grammar."""

from __future__ import annotations

from pathlib import Path

from uge import Grammar

GRAMMAR_ID = "trading_mvp"
_GRAMMAR_PATH = Path(__file__).resolve().parent / "grammars" / "trading_mvp.bnf"


def trading_mvp_bnf_path() -> Path:
    return _GRAMMAR_PATH


def load_trading_mvp_grammar() -> Grammar:
    """Load checked-in discrete-param MVP grammar."""
    return Grammar.from_path(_GRAMMAR_PATH)


def trading_mvp_bnf_text() -> str:
    return _GRAMMAR_PATH.read_text(encoding="utf-8")
