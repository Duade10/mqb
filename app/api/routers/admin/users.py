from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import AdminRoleEnum, AdminUser
from app.schemas.auth import AdminProfile, AdminUpdateRequest


router = APIRouter(prefix="/admin/users", tags=["Admin"])


def _ensure_admin_privileges(user: AdminUser) -> None:
    if user.role not in {AdminRoleEnum.ADMIN.value, AdminRoleEnum.SUPERADMIN.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")


@router.get("", response_model=list[AdminProfile])
def list_admins(
    db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)
) -> list[AdminProfile]:
    _ensure_admin_privileges(current_admin)
    users = db.query(AdminUser).order_by(AdminUser.id).all()
    return [AdminProfile.from_orm(user) for user in users]


@router.put("/{user_id}", response_model=AdminProfile)
def update_admin(
    user_id: int,
    payload: AdminUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminProfile:
    _ensure_admin_privileges(current_admin)

    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    if payload.role:
        if payload.role not in {role.value for role in AdminRoleEnum}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminProfile.from_orm(user)

