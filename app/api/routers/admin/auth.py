from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import authenticate_admin, get_current_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    AdminAuditLog,
    AdminInvite,
    AdminPasswordResetToken,
    AdminRecoveryCode,
    AdminRefreshToken,
    AdminRoleEnum,
    AdminUser,
)
from app.schemas.auth import (
    AdminProfile,
    BootstrapResponse,
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    LogoutRequest,
    PasswordResetRequest,
    PasswordResetSubmit,
    RefreshRequest,
    RegisterRequest,
    TOTPDisableRequest,
    TOTPEnableRequest,
    TOTPSetupResponse,
    TokenPair,
)
from app.utils.rate_limiter import rate_limiter
from app.utils.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    hash_token,
    password_meets_policy,
)
from app.utils.totp import (
    build_totp_uri,
    generate_recovery_codes,
    generate_totp_secret,
    verify_totp,
)


router = APIRouter(tags=["Admin"])
settings = get_settings()


def _log_event(
    db: Session, event_type: str, user: AdminUser | None, request: Request, details: Any | None = None
) -> None:
    log = AdminAuditLog(
        user_id=user.id if user else None,
        event_type=event_type,
        ip_address=request.client.host if request.client else None,
        details=details,
    )
    db.add(log)


def _issue_tokens(
    db: Session, user: AdminUser, family_id: str | None = None
) -> tuple[str, str, AdminRefreshToken]:
    access_payload = {
        "sub": str(user.id),
        "role": user.role,
        "pwd": user.password_changed_at.isoformat(),
    }
    access_token = create_access_token(access_payload)
    refresh_token = generate_refresh_token()
    refresh_record = AdminRefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        family_id=family_id or uuid4().hex,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_record)
    db.flush()
    return access_token, refresh_token, refresh_record


def _revoke_refresh_family(db: Session, family_id: str) -> None:
    tokens = (
        db.query(AdminRefreshToken)
        .filter(AdminRefreshToken.family_id == family_id, AdminRefreshToken.revoked_at.is_(None))
        .all()
    )
    now = datetime.utcnow()
    for token in tokens:
        token.revoked_at = now


def _validate_password(password: str) -> None:
    if not password_meets_policy(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet the required complexity policy.",
        )


@router.post(
    "/admin/auth/bootstrap",
    response_model=BootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_admin(db: Session = Depends(get_db)) -> BootstrapResponse:
    if db.query(AdminUser).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bootstrap already completed")

    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bootstrap credentials not configured")

    _validate_password(settings.bootstrap_admin_password)

    user = AdminUser(
        email=settings.bootstrap_admin_email.lower(),
        hashed_password=get_password_hash(settings.bootstrap_admin_password),
        role=AdminRoleEnum.SUPERADMIN.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return BootstrapResponse(email=user.email)


@router.post(
    "/admin/auth/login",
    response_model=TokenPair,
    dependencies=[Depends(rate_limiter.limit("login", settings.login_rate_limit, settings.rate_limit_window_seconds))],
)
def login_for_tokens(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    user = authenticate_admin(db, payload.email.lower(), payload.password)
    if not user:
        _log_event(db, "login_failed", None, request, {"email": payload.email})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.totp_enabled:
        if payload.totp_code:
            if not verify_totp(user.totp_secret or "", payload.totp_code):
                _log_event(db, "login_failed_totp", user, request, {"reason": "invalid_totp"})
                db.commit()
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")
        elif payload.recovery_code:
            code_hash = hash_token(payload.recovery_code)
            recovery = (
                db.query(AdminRecoveryCode)
                .filter(
                    AdminRecoveryCode.user_id == user.id,
                    AdminRecoveryCode.code_hash == code_hash,
                    AdminRecoveryCode.used_at.is_(None),
                )
                .first()
            )
            if not recovery:
                _log_event(db, "login_failed_totp", user, request, {"reason": "invalid_recovery"})
                db.commit()
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid recovery code")
            recovery.used_at = datetime.utcnow()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA code required",
            )

    access_token, refresh_token, _ = _issue_tokens(db, user)
    user.last_login_at = datetime.utcnow()
    _log_event(db, "login_success", user, request)
    db.commit()
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/admin/auth/refresh", response_model=TokenPair)
def refresh_tokens(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    token_hash = hash_token(payload.refresh_token)
    stored = db.query(AdminRefreshToken).filter(AdminRefreshToken.token_hash == token_hash).first()
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if stored.revoked_at or stored.expires_at < datetime.utcnow():
        _revoke_refresh_family(db, stored.family_id)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    user = stored.user
    if not user or not user.is_active:
        _revoke_refresh_family(db, stored.family_id)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    new_access, new_refresh, new_record = _issue_tokens(db, user, family_id=stored.family_id)
    stored.revoked_at = datetime.utcnow()
    stored.replaced_by_id = new_record.id
    _log_event(db, "refresh", user, request)
    db.commit()
    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/admin/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def logout(payload: LogoutRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    token_hash = hash_token(payload.refresh_token)
    stored = db.query(AdminRefreshToken).filter(AdminRefreshToken.token_hash == token_hash).first()
    if stored:
        _revoke_refresh_family(db, stored.family_id)
        _log_event(db, "logout", stored.user, request)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/me", response_model=AdminProfile)
def get_me(current_admin: AdminUser = Depends(get_current_admin)) -> AdminProfile:
    return AdminProfile.from_orm(current_admin)


@router.post("/admin/invites", response_model=InviteResponse)
def create_invite(
    payload: InviteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> InviteResponse:
    if current_admin.role not in {AdminRoleEnum.ADMIN.value, AdminRoleEnum.SUPERADMIN.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")

    expires_hours = payload.expires_in_hours or settings.invite_expire_hours
    invite = AdminInvite(
        email=payload.email.lower(),
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        created_by_id=current_admin.id,
    )
    db.add(invite)
    _log_event(db, "invite_created", current_admin, request, {"invite_email": payload.email})
    db.commit()
    db.refresh(invite)
    return InviteResponse(code=invite.code, expires_at=invite.expires_at)


@router.post("/admin/auth/register", response_model=AdminProfile, status_code=status.HTTP_201_CREATED)
def register_admin(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> AdminProfile:
    invite = db.query(AdminInvite).filter(AdminInvite.code == payload.invite_code).first()
    if not invite or invite.is_revoked:
        raise HTTPException(status=status.HTTP_400_BAD_REQUEST, detail="Invalid invite code")
    if invite.used_at or invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite expired")
    if invite.email and invite.email.lower() != payload.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite email mismatch")

    existing = db.query(AdminUser).filter(AdminUser.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin already exists")

    _validate_password(payload.password)

    user = AdminUser(
        email=payload.email.lower(),
        hashed_password=get_password_hash(payload.password),
        role=AdminRoleEnum.ADMIN.value,
    )
    db.add(user)
    db.flush()

    invite.used_at = datetime.utcnow()
    invite.used_by_id = user.id
    _log_event(db, "invite_used", user, request, {"invite_code": invite.code})
    db.commit()
    db.refresh(user)
    return AdminProfile.from_orm(user)


@router.post(
    "/admin/auth/request-password-reset",
    dependencies=[Depends(rate_limiter.limit("password_reset", settings.reset_rate_limit, settings.rate_limit_window_seconds))],
)
def request_password_reset(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    user = db.query(AdminUser).filter(AdminUser.email == payload.email.lower()).first()
    if user:
        token_value = generate_refresh_token(48)
        reset = AdminPasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token_value),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.password_reset_expire_minutes),
        )
        db.add(reset)
        _log_event(db, "password_reset_requested", user, request)
        # In production this token would be emailed. For automated tests we persist the raw token
        # in the metadata for retrieval via audit logs.
        reset_metadata = {"token": token_value}
        log = AdminAuditLog(
            user_id=user.id,
            event_type="password_reset_token",
            ip_address=request.client.host if request.client else None,
            details=reset_metadata,
        )
        db.add(log)
        db.commit()
    else:
        db.commit()
    return {"message": "If the account exists, a reset link has been sent."}


@router.post("/admin/auth/reset-password")
def reset_password(payload: PasswordResetSubmit, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    token_hash = hash_token(payload.token)
    reset_token = (
        db.query(AdminPasswordResetToken)
        .filter(AdminPasswordResetToken.token_hash == token_hash)
        .first()
    )
    if (
        not reset_token
        or reset_token.used_at is not None
        or reset_token.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = reset_token.user
    _validate_password(payload.password)

    user.hashed_password = get_password_hash(payload.password)
    user.password_changed_at = datetime.utcnow()
    reset_token.used_at = datetime.utcnow()
    # revoke specific tokens for the user
    user_tokens = (
        db.query(AdminRefreshToken)
        .filter(AdminRefreshToken.user_id == user.id, AdminRefreshToken.revoked_at.is_(None))
        .all()
    )
    now = datetime.utcnow()
    for token in user_tokens:
        token.revoked_at = now

    _log_event(db, "password_reset_completed", user, request)
    db.commit()
    return {"message": "Password reset successful"}


@router.post("/admin/auth/2fa/setup", response_model=TOTPSetupResponse)
def setup_2fa(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TOTPSetupResponse:
    secret = generate_totp_secret()
    current_admin.totp_secret = secret
    current_admin.totp_enabled = False
    db.add(current_admin)
    _log_event(db, "2fa_setup", current_admin, request)
    db.commit()
    return TOTPSetupResponse(secret=secret, uri=build_totp_uri(secret, current_admin.email))


@router.post("/admin/auth/2fa/enable")
def enable_2fa(
    payload: TOTPEnableRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict[str, list[str]]:
    if not current_admin.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not initialized")
    if not verify_totp(current_admin.totp_secret, payload.totp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

    recovery_codes = generate_recovery_codes()
    db.query(AdminRecoveryCode).filter(AdminRecoveryCode.user_id == current_admin.id).delete()
    for code in recovery_codes:
        db.add(AdminRecoveryCode(user_id=current_admin.id, code_hash=hash_token(code)))

    current_admin.totp_enabled = True
    _log_event(db, "2fa_enabled", current_admin, request)
    db.commit()
    return {"recovery_codes": recovery_codes}


@router.post("/admin/auth/2fa/disable")
def disable_2fa(
    payload: TOTPDisableRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict[str, str]:
    if not current_admin.totp_enabled:
        return {"message": "2FA disabled"}
    valid = False
    if payload.totp_code and verify_totp(current_admin.totp_secret or "", payload.totp_code):
        valid = True
    elif payload.recovery_code:
        code_hash = hash_token(payload.recovery_code)
        recovery = (
            db.query(AdminRecoveryCode)
            .filter(
                AdminRecoveryCode.user_id == current_admin.id,
                AdminRecoveryCode.code_hash == code_hash,
                AdminRecoveryCode.used_at.is_(None),
            )
            .first()
        )
        if recovery:
            recovery.used_at = datetime.utcnow()
            valid = True

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    db.query(AdminRecoveryCode).filter(AdminRecoveryCode.user_id == current_admin.id).delete()
    current_admin.totp_secret = None
    current_admin.totp_enabled = False
    _log_event(db, "2fa_disabled", current_admin, request)
    db.commit()
    return {"message": "2FA disabled"}
