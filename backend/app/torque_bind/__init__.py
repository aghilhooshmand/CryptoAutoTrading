"""Torque bind / evaluate — FORGE form + CryptoAutoTrading strategy binding."""

from app.torque_bind.bind import (
    BoundCompose,
    BoundLeaf,
    BoundProgram,
    CheckPhenotypeResult,
    bind_phenotype,
    bind_to_program,
    check_phenotype,
    collect_effective_leaves,
    ensure_strategies_registered,
)
from app.torque_bind.catalogue import (
    COMPOSITION_OPS,
    MVP_LEAF_IDS,
    leaf_param_metadata,
    mvp_leaf_catalogue,
)
from app.torque_bind.compose import CompositeStrategy, combine_and, combine_or, combine_vote
from app.torque_bind.errors import (
    ERROR_CODES,
    EVALUATE_FAILED,
    INVALID_COMPOSITION,
    INVALID_TORQUE_FORM,
    INVALID_TORQUE_PARAMS,
    UNKNOWN_TORQUE_LEAF,
    TorqueBindError,
)
from app.torque_bind.evaluate import evaluate_phenotype, run_bound_backtest

__all__ = [
    "BoundCompose",
    "BoundLeaf",
    "BoundProgram",
    "COMPOSITION_OPS",
    "CheckPhenotypeResult",
    "CompositeStrategy",
    "ERROR_CODES",
    "EVALUATE_FAILED",
    "INVALID_COMPOSITION",
    "INVALID_TORQUE_FORM",
    "INVALID_TORQUE_PARAMS",
    "MVP_LEAF_IDS",
    "TorqueBindError",
    "UNKNOWN_TORQUE_LEAF",
    "bind_phenotype",
    "bind_to_program",
    "check_phenotype",
    "collect_effective_leaves",
    "combine_and",
    "combine_or",
    "combine_vote",
    "ensure_strategies_registered",
    "evaluate_phenotype",
    "leaf_param_metadata",
    "mvp_leaf_catalogue",
    "run_bound_backtest",
]
