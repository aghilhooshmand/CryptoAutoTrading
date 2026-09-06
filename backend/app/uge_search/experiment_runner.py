"""Singleton in-process Evolution experiment job (Feature 020)."""

from __future__ import annotations

import threading
from typing import Any, Callable

from app.uge_search import experiment_store as store


class ExperimentConflictError(Exception):
    def __init__(self, message: str = "Another evolution experiment is already active") -> None:
        super().__init__(message)
        self.code = "experiment_already_running"
        self.message = message


class ExperimentRunner:
    """At most one active experiment; background thread; cancel at gen boundary."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_id: str | None = None
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def active_id(self) -> str | None:
        return self._active_id

    def is_active(self) -> bool:
        with self._lock:
            return self._active_id is not None and (
                self._thread is not None and self._thread.is_alive()
            )

    def request_cancel(self, experiment_id: str) -> bool:
        with self._lock:
            if self._active_id != experiment_id:
                return False
            self._cancel.set()
            return True

    def start(
        self,
        experiment_id: str,
        target: Callable[[], None],
    ) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise ExperimentConflictError()
            self._cancel.clear()
            self._active_id = experiment_id

            def _wrap() -> None:
                try:
                    target()
                finally:
                    with self._lock:
                        if self._active_id == experiment_id:
                            self._active_id = None
                        self._thread = None

            self._thread = threading.Thread(
                target=_wrap,
                name=f"uge-experiment-{experiment_id}",
                daemon=True,
            )
            self._thread.start()

    def cancel_requested(self) -> bool:
        return self._cancel.is_set()


_RUNNER = ExperimentRunner()


def get_experiment_runner() -> ExperimentRunner:
    return _RUNNER


def reset_experiment_runner_for_tests() -> ExperimentRunner:
    """Test helper — replace singleton with a fresh runner."""
    global _RUNNER
    _RUNNER = ExperimentRunner()
    return _RUNNER


def public_experiment_view(meta: dict[str, Any], *, include_generations: bool = False) -> dict[str, Any]:
    out = dict(meta)
    if include_generations:
        out["generations"] = store.read_generations(str(meta["id"]))
    return out
