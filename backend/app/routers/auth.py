from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.database import get_db
from app.models.models import User

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    created_at: datetime


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == credentials.email))
    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token({"sub": user.email, "role": role})
    return TokenResponse(access_token=access_token, token_type="bearer", role=role)


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        role=role,
        created_at=current_user.created_at,
    )
