"""Backend health capability (Feature 001)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return process readiness for local developer and automated checks."""
    return {"status": "healthy"}
