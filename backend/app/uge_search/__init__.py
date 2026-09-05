"""UGE Grammatical Evolution search — FORGE uge + Feature 016 fitness."""

from app.uge_search.fitness import (
    DEFAULT_FITNESS_ID,
    FITNESS_ALLOW_LIST,
    FITNESS_NET_MINUS_BH,
    FITNESS_NET_PROFIT,
    make_backtest_evaluator,
    resolve_fitness_id,
    scalar_from_metrics,
    score_phenotype,
)
from app.uge_search.grammar_mvp import (
    GRAMMAR_ID,
    load_trading_mvp_grammar,
    trading_mvp_bnf_path,
    trading_mvp_bnf_text,
)
from app.uge_search.persist import (
    list_frozen_artifacts,
    load_frozen_artifact,
    load_frozen_phenotype,
    persist_run_result,
    uge_runs_dir,
)
from app.uge_search.runner import UgeRunResult, run_uge_search
from app.uge_search.splits import ChronologicalSplit, chronological_split

__all__ = [
    "ChronologicalSplit",
    "DEFAULT_FITNESS_ID",
    "FITNESS_ALLOW_LIST",
    "FITNESS_NET_MINUS_BH",
    "FITNESS_NET_PROFIT",
    "GRAMMAR_ID",
    "UgeRunResult",
    "chronological_split",
    "list_frozen_artifacts",
    "load_frozen_artifact",
    "load_frozen_phenotype",
    "load_trading_mvp_grammar",
    "make_backtest_evaluator",
    "persist_run_result",
    "resolve_fitness_id",
    "run_uge_search",
    "scalar_from_metrics",
    "score_phenotype",
    "trading_mvp_bnf_path",
    "trading_mvp_bnf_text",
    "uge_runs_dir",
]
