from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.models import AdminRoleEnum, AdminUser
from app.utils.rate_limiter import rate_limiter
from app.utils.security import get_password_hash
from tests.conftest import SimpleTestClient
from tests.test_admin_auth import login


def _create_admin(db_session: Session, email: str) -> AdminUser:
    rate_limiter._buckets.clear()
    admin = AdminUser(
        email=email,
        hashed_password=get_password_hash("Secretpass1!"),
        role=AdminRoleEnum.SUPERADMIN.value,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def test_generate_qr_from_url(client: SimpleTestClient, db_session: Session) -> None:
    admin = _create_admin(db_session, "qr-admin3@example.com")
    tokens = login(client, admin.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.get(
        "/admin/qr", params={"url": "https://example.com/path?query=1"}, headers=headers
    )

    assert response.status_code in (302, 303, 307)
    location = response.headers.get("location")
    assert location and location.startswith("https://api.qrserver.com/v1/create-qr-code/")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert params.get("data") == ["https://example.com/path?query=1"]


def test_generate_qr_from_url_requires_param(client: SimpleTestClient, db_session: Session) -> None:
    admin = _create_admin(db_session, "qr-admin4@example.com")
    tokens = login(client, admin.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.get("/admin/qr", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "A URL parameter is required to generate a QR code"


def test_generate_qr_requires_authentication(client: SimpleTestClient) -> None:
    response = client.get("/admin/qr", params={"url": "https://example.com"})

    assert response.status_code == 401
