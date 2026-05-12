"""Password hashing, JWT handling, and current-user dependencies."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    claims = data.copy()
    claims["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        if not isinstance(email, str):
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise credentials_exception

    return user


def require_role(role: str) -> Callable[[User], User]:
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role.value != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency
