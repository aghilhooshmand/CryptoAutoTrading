"""Recovery re-export covered in test_state_machine; keep module importable."""

from app.simulation.recovery import recover_orphan_sessions


def test_import():
    assert callable(recover_orphan_sessions)
