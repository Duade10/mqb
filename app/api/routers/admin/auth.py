from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import authenticate_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import Token
from app.utils.security import create_access_token

router = APIRouter()
settings = get_settings()


@router.post("/admin/auth/token", response_model=Token, tags=["Admin"])
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    user = authenticate_admin(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(access_token=access_token)
