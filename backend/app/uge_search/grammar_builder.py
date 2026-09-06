"""Structured search-space → FORGE Grammar (Feature 020b)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from uge import Grammar

from app.uge_search.errors import INVALID_SEARCH_SPACE, UgeSearchError

DEFAULT_LEAVES = ("rsi", "dual_ema", "macd")
DEFAULT_OPS = ("and", "or", "vote")

DEFAULT_PARAM_ALTS: dict[str, list[int]] = {
    "rsi.period": [7, 10, 14, 21],
    "dual_ema.fastPeriod": [5, 9, 12],
    "dual_ema.slowPeriod": [13, 21, 26],
    "macd.fastPeriod": [8, 12],
    "macd.slowPeriod": [17, 26],
    "macd.signalPeriod": [5, 9],
}


@dataclass
class BuiltGrammar:
    grammar: Grammar
    grammar_id: str
    bnf_text: str


def _alts(values: Sequence[int]) -> str:
    if not values:
        raise UgeSearchError(INVALID_SEARCH_SPACE, "Parameter alternative list is empty")
    return " | ".join(str(int(v)) for v in values)


def build_grammar(
    leaves: Sequence[str] | None = None,
    composition_ops: Sequence[str] | None = None,
    param_alternatives: dict[str, Sequence[int]] | None = None,
) -> BuiltGrammar:
    """
    Build a discrete-param BNF from structured controls (no raw operator BNF).
    """
    leaf_ids = [
        str(x).strip()
        for x in (DEFAULT_LEAVES if leaves is None else leaves)
        if str(x).strip()
    ]
    ops = [
        str(x).strip().lower()
        for x in (DEFAULT_OPS if composition_ops is None else composition_ops)
        if str(x).strip()
    ]
    if not leaf_ids:
        raise UgeSearchError(INVALID_SEARCH_SPACE, "At least one strategy leaf is required")
    allowed_leaves = set(DEFAULT_LEAVES)
    for lid in leaf_ids:
        if lid not in allowed_leaves:
            raise UgeSearchError(INVALID_SEARCH_SPACE, f"Unknown leaf: {lid}")
    allowed_ops = set(DEFAULT_OPS)
    for op in ops:
        if op not in allowed_ops:
            raise UgeSearchError(INVALID_SEARCH_SPACE, f"Unknown composition op: {op}")

    alts = dict(DEFAULT_PARAM_ALTS)
    if param_alternatives:
        for key, vals in param_alternatives.items():
            alts[str(key)] = [int(v) for v in vals]

    leaf_forms: list[str] = []
    if "rsi" in leaf_ids:
        leaf_forms.append(f"rsi(period=<rsi_period>, oversold=30, overbought=70)")
    if "dual_ema" in leaf_ids:
        leaf_forms.append("dual_ema(fastPeriod=<ema_fast>, slowPeriod=<ema_slow>)")
    if "macd" in leaf_ids:
        leaf_forms.append(
            "macd(fastPeriod=<macd_fast>, slowPeriod=<macd_slow>, signalPeriod=<macd_sig>)"
        )
    leaf_rule = " | ".join(leaf_forms)

    compose_forms: list[str] = []
    for op in ops:
        compose_forms.append(f"{op}(<leaf>, <leaf>)")

    if compose_forms:
        program = "<leaf> | <compose>"
        compose_rule = " | ".join(compose_forms)
        compose_block = f"<compose> ::= {compose_rule}\n"
    else:
        program = "<leaf>"
        compose_block = ""

    bnf = f"""# Structured grammar (Feature 020b) — system-built; not operator raw BNF.
<program> ::= {program}
{compose_block}<leaf> ::= {leaf_rule}
<rsi_period> ::= {_alts(alts['rsi.period'])}
<ema_fast> ::= {_alts(alts['dual_ema.fastPeriod'])}
<ema_slow> ::= {_alts(alts['dual_ema.slowPeriod'])}
<macd_fast> ::= {_alts(alts['macd.fastPeriod'])}
<macd_slow> ::= {_alts(alts['macd.slowPeriod'])}
<macd_sig> ::= {_alts(alts['macd.signalPeriod'])}
"""
    grammar = Grammar.from_text(bnf)
    gid = "structured_" + "_".join(sorted(leaf_ids)) + "_" + "-".join(sorted(ops) or ["leaf"])
    return BuiltGrammar(grammar=grammar, grammar_id=gid[:80], bnf_text=bnf)
