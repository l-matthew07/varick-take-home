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

    access_token = create_access_token({"sub": user.email, "role": user.role.value})
    return TokenResponse(access_token=access_token, token_type="bearer", role=user.role.value)


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        created_at=current_user.created_at,
    )
