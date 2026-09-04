"""Check + bind Torque phenotypes to Strategy instances (Feature 016)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal as TypingLiteral

from app.strategy.base import Strategy
from app.strategy.params import StrategyParamError
from app.strategy.registry import UnknownStrategyError, validate_and_materialize
from app.torque_bind.catalogue import (
    is_composition_name,
    normalize_composition_op,
    resolve_leaf_id,
)
from app.torque_bind.compose import CompositeStrategy
from app.torque_bind.errors import (
    INVALID_COMPOSITION,
    INVALID_TORQUE_FORM,
    INVALID_TORQUE_PARAMS,
    UNKNOWN_TORQUE_LEAF,
    TorqueBindError,
)


def ensure_strategies_registered() -> None:
    """Import strategy modules so registry auto-register side effects run."""
    import app.strategy  # noqa: F401


@dataclass
class CheckPhenotypeResult:
    ok: bool
    program: Any = None
    error: TorqueBindError | None = None


@dataclass
class BoundLeaf:
    kind: TypingLiteral["leaf"]
    strategy_id: str
    params: dict[str, Any]
    strategy: Strategy


@dataclass
class BoundCompose:
    kind: TypingLiteral["compose"]
    op: str
    children: list[BoundLeaf | BoundCompose]
    strategy: CompositeStrategy


BoundNode = BoundLeaf | BoundCompose


@dataclass
class BoundProgram:
    source: str
    root: BoundNode


def check_phenotype(source: str) -> CheckPhenotypeResult:
    """Wrap FORGE ``torque.check``; map FormError → invalid_torque_form."""
    text = "" if source is None else str(source)
    if not text.strip():
        return CheckPhenotypeResult(
            ok=False,
            error=TorqueBindError(INVALID_TORQUE_FORM, "Phenotype source is empty"),
        )
    from torque import check

    result = check(text)
    if not result.ok:
        msg = str(result.error) if result.error is not None else "Invalid Torque form"
        return CheckPhenotypeResult(
            ok=False,
            error=TorqueBindError(INVALID_TORQUE_FORM, msg),
        )
    return CheckPhenotypeResult(ok=True, program=result.program)


def _literal_to_python(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value


def _keywords_to_params(keywords: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for item in keywords or ():
        if not isinstance(item, tuple) or len(item) != 2:
            raise TorqueBindError(
                INVALID_TORQUE_PARAMS,
                f"Invalid keyword pair: {item!r}",
            )
        key, lit = item
        params[str(key)] = _literal_to_python(lit)
    return params


def _bind_instruction(node: Any) -> BoundNode:
    name = getattr(node, "name", None)
    if name is None:
        raise TorqueBindError(INVALID_TORQUE_FORM, "Instruction missing name")

    positional = tuple(getattr(node, "positional", ()) or ())
    keywords = tuple(getattr(node, "keywords", ()) or ())

    if is_composition_name(str(name)):
        op = normalize_composition_op(str(name))
        assert op is not None
        if keywords:
            raise TorqueBindError(
                INVALID_COMPOSITION,
                f"Composition '{op}' does not accept keyword arguments",
            )
        if len(positional) < 2:
            raise TorqueBindError(
                INVALID_COMPOSITION,
                f"Composition '{op}' requires at least 2 children",
            )
        children: list[BoundNode] = []
        for child in positional:
            child_name = getattr(child, "name", None)
            if child_name is None:
                raise TorqueBindError(
                    INVALID_COMPOSITION,
                    f"Composition '{op}' children must be instructions, not literals",
                )
            children.append(_bind_instruction(child))
        strategies = [c.strategy for c in children]
        composite = CompositeStrategy(op, strategies)
        return BoundCompose(kind="compose", op=op, children=children, strategy=composite)

    # Leaf
    if positional:
        raise TorqueBindError(
            INVALID_TORQUE_PARAMS,
            "Leaf strategies require keyword parameters only (positional args out of MVP)",
        )
    leaf_id = resolve_leaf_id(str(name))
    if leaf_id is None:
        raise TorqueBindError(UNKNOWN_TORQUE_LEAF, f"Unknown Torque leaf: {name}")
    params = _keywords_to_params(keywords)
    try:
        canonical, effective, instance = validate_and_materialize(leaf_id, params)
    except UnknownStrategyError as exc:
        raise TorqueBindError(UNKNOWN_TORQUE_LEAF, str(exc)) from exc
    except StrategyParamError as exc:
        raise TorqueBindError(INVALID_TORQUE_PARAMS, exc.message) from exc
    return BoundLeaf(kind="leaf", strategy_id=canonical, params=effective, strategy=instance)


def bind_to_program(source: str) -> BoundProgram:
    """Check + bind to BoundProgram tree. Raises TorqueBindError on failure."""
    ensure_strategies_registered()
    checked = check_phenotype(source)
    if not checked.ok:
        assert checked.error is not None
        raise checked.error
    root = _bind_instruction(checked.program.root)
    return BoundProgram(source=str(source).strip(), root=root)


def bind_phenotype(source: str) -> Strategy:
    """Check + bind; return Strategy (leaf or CompositeStrategy). Raises on failure."""
    return bind_to_program(source).root.strategy


def collect_effective_leaves(node: BoundNode) -> list[dict[str, Any]]:
    if node.kind == "leaf":
        return [{"strategyId": node.strategy_id, "params": dict(node.params)}]
    leaves: list[dict[str, Any]] = []
    for child in node.children:
        leaves.extend(collect_effective_leaves(child))
    return leaves
