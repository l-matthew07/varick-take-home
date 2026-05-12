from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def health_check(db: Session = Depends(get_db)) -> dict[str, str] | JSONResponse:
    timestamp = datetime.now(UTC).isoformat()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "db": "error", "timestamp": timestamp},
        )

    return {"status": "healthy", "db": "connected", "timestamp": timestamp}
