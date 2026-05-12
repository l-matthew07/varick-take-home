from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "db": "not_checked",
        "timestamp": datetime.now(UTC).isoformat(),
    }
