import json

from sqlalchemy.orm import Session

from app.models import AdminAuditLog, AdminInvite, AdminPasswordResetToken, AdminUser
from tests.conftest import SimpleTestClient


def login(client: SimpleTestClient, email: str, password: str) -> dict:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_admin_login_returns_tokens(client: SimpleTestClient, admin_user: AdminUser) -> None:
    data = login(client, admin_user.email, "Secretpass1!")
    assert "access_token" in data and "refresh_token" in data


def test_protected_route_requires_token(client: SimpleTestClient) -> None:
    response = client.get("/admin/me")
    assert response.status_code == 401


def test_refresh_rotates_token(client: SimpleTestClient, db_session: Session, admin_user: AdminUser) -> None:
    tokens = login(client, admin_user.email, "Secretpass1!")
    refresh = tokens["refresh_token"]

    refresh_resp = client.post("/admin/auth/refresh", json={"refresh_token": refresh})
    assert refresh_resp.status_code == 200
    refreshed = refresh_resp.json()
    assert refreshed["refresh_token"] != refresh

    reuse_resp = client.post("/admin/auth/refresh", json={"refresh_token": refresh})
    assert reuse_resp.status_code == 401


def test_invite_and_register_flow(client: SimpleTestClient, db_session: Session, admin_user: AdminUser) -> None:
    tokens = login(client, admin_user.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    invite_resp = client.post("/admin/invites", json={"email": "new-admin@example.com"}, headers=headers)
    assert invite_resp.status_code == 200
    invite_code = invite_resp.json()["code"]

    register_resp = client.post(
        "/admin/auth/register",
        json={"email": "new-admin@example.com", "password": "Anotherpass1!", "invite_code": invite_code},
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == "new-admin@example.com"

    new_user = db_session.query(AdminUser).filter(AdminUser.email == "new-admin@example.com").first()
    assert new_user is not None
    assert db_session.query(AdminInvite).filter(AdminInvite.code == invite_code).first().used_at is not None


def test_password_reset_flow(client: SimpleTestClient, db_session: Session, admin_user: AdminUser) -> None:
    request_resp = client.post(
        "/admin/auth/request-password-reset",
        json={"email": admin_user.email},
    )
    assert request_resp.status_code == 200

    reset_token = (
        db_session.query(AdminPasswordResetToken)
        .filter(AdminPasswordResetToken.user_id == admin_user.id)
        .order_by(AdminPasswordResetToken.id.desc())
        .first()
    )
    assert reset_token is not None

    audit_log = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.event_type == "password_reset_token")
        .order_by(AdminAuditLog.id.desc())
        .first()
    )
    assert audit_log is not None
    raw_metadata = audit_log.details
    if isinstance(raw_metadata, str):
        raw_metadata = json.loads(raw_metadata)
    raw_token = raw_metadata["token"]

    reset_resp = client.post(
        "/admin/auth/reset-password",
        json={"token": raw_token, "password": "Resetpass12!"},
    )
    assert reset_resp.status_code == 200

    login(client, admin_user.email, "Resetpass12!")
