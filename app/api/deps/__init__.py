from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import AdminUser
from app.utils.security import verify_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/auth/token")
settings = get_settings()


def authenticate_admin(db: Session, username: str, password: str) -> Optional[AdminUser]:
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_admin(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AdminUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError as exc:  # type: ignore[attr-defined]
        raise credentials_exception from exc
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
