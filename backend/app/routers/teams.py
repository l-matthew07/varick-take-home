from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import Team, User

router = APIRouter(tags=["teams"])


@router.get("/teams", response_model=list[str])
def list_teams(
    _: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[str]:
    return list(db.scalars(select(Team.name).order_by(Team.name)))
