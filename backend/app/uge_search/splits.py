"""Chronological train / validation / test split (Feature 021 min)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

from app.uge_search.errors import INVALID_SPLIT, UgeSearchError

T = TypeVar("T")


@dataclass(frozen=True)
class ChronologicalSplit(Generic[T]):
    train: list[T]
    validation: list[T]
    test: list[T]
    train_ratio: float
    val_ratio: float
    test_ratio: float


def chronological_split(
    items: Sequence[T],
    *,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
) -> ChronologicalSplit[T]:
    """
    Contiguous chronological split by count ratios (no shuffle).

    ``items`` MUST already be ordered oldest → newest (e.g. by openTime).
    """
    total_r = train_ratio + val_ratio + test_ratio
    if abs(total_r - 1.0) > 1e-9:
        raise UgeSearchError(
            INVALID_SPLIT,
            f"Split ratios must sum to 1.0, got {total_r}",
        )
    if any(r < 0 for r in (train_ratio, val_ratio, test_ratio)):
        raise UgeSearchError(INVALID_SPLIT, "Split ratios must be non-negative")
    n = len(items)
    if n < 3:
        raise UgeSearchError(
            INVALID_SPLIT,
            f"Need at least 3 candles for train/val/test, got {n}",
        )
    n_train = max(1, int(n * train_ratio))
    n_val = max(1, int(n * val_ratio))
    # Remainder to test so all candles used
    if n_train + n_val >= n:
        n_train = max(1, n - 2)
        n_val = 1
    n_test = n - n_train - n_val
    if n_test < 1:
        n_test = 1
        n_val = max(1, n - n_train - n_test)
        n_train = n - n_val - n_test
    train = list(items[:n_train])
    validation = list(items[n_train : n_train + n_val])
    test = list(items[n_train + n_val :])
    return ChronologicalSplit(
        train=train,
        validation=validation,
        test=test,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
    )
