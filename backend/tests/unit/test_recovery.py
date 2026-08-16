"""Recovery re-export covered in test_state_machine; keep module importable."""

from app.simulation.recovery import recover_orphan_sessions, recover_orphan_sessions_async


def test_import():
    assert callable(recover_orphan_sessions)
    assert callable(recover_orphan_sessions_async)
