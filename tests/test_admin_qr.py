from urllib.parse import urlparse, parse_qs

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AdminRoleEnum, AdminUser
from app.schemas.listing import ListingOut
from app.services.qr import create_qr_token
from app.utils.rate_limiter import rate_limiter
from app.utils.security import get_password_hash
from tests.conftest import SimpleTestClient
from tests.test_admin_auth import login

settings = get_settings()


def test_admin_can_generate_listing_qr_link(
    client: SimpleTestClient, db_session: Session
) -> None:
    rate_limiter._buckets.clear()
    admin = AdminUser(
        email="qr-admin@example.com",
        hashed_password=get_password_hash("Secretpass1!"),
        role=AdminRoleEnum.SUPERADMIN.value,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    tokens = login(client, admin.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    listing_resp = client.post(
        "/admin/listings",
        json={"name": "Test Listing", "slug": "test-listing"},
        headers=headers,
    )
    assert listing_resp.status_code == 200
    listing = ListingOut(**listing_resp.json())

    qr_resp = client.get(
        f"/admin/listings/{listing.id}/qr",
        headers=headers,
        params={"require_consent": True},
    )
    assert qr_resp.status_code in (302, 303, 307)
    location = qr_resp.headers.get("location")
    assert location and location.startswith("https://api.qrserver.com/v1/create-qr-code/")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert "data" in params
    settings = get_settings()
    expected_base = (settings.public_frontend_base_url or "").rstrip("/")
    assert (
        params["data"][0]
        == f"{expected_base}/public/listings/{listing.id}?require_consent=true"
    )

    qr_token_resp = client.post(
        f"/admin/listings/{listing.id}/qr",
        json={"require_consent": False},
        headers=headers,
    )
    assert qr_token_resp.status_code == 200
    qr_payload = qr_token_resp.json()
    assert qr_payload["require_consent"] is False


def test_admin_can_generate_listing_qr_without_consent(
    client: SimpleTestClient, db_session: Session
) -> None:
    rate_limiter._buckets.clear()
    admin = AdminUser(
        email="qr-admin2@example.com",
        hashed_password=get_password_hash("Secretpass1!"),
        role=AdminRoleEnum.SUPERADMIN.value,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    tokens = login(client, admin.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    listing_resp = client.post(
        "/admin/listings",
        json={"name": "Test Listing 2", "slug": "test-listing-2"},
        headers=headers,
    )
    assert listing_resp.status_code == 200
    listing = ListingOut(**listing_resp.json())

    qr_resp = client.get(
        f"/admin/listings/{listing.id}/qr",
        headers=headers,
        params={"require_consent": False},
    )
    assert qr_resp.status_code in (302, 303, 307)
    location = qr_resp.headers.get("location")
    assert location and location.startswith("https://api.qrserver.com/v1/create-qr-code/")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert "data" in params
    expected_base = (settings.public_frontend_base_url or "").rstrip("/")
    assert params["data"][0] == f"{expected_base}/public/listings/{listing.id}"


def test_admin_can_resolve_qr_token(client: SimpleTestClient, db_session: Session) -> None:
    rate_limiter._buckets.clear()
    admin = AdminUser(
        email="qr-admin-resolve@example.com",
        hashed_password=get_password_hash("Secretpass1!"),
        role=AdminRoleEnum.SUPERADMIN.value,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    tokens = login(client, admin.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    listing_resp = client.post(
        "/admin/listings",
        json={"name": "Resolve Listing", "slug": "resolve-listing"},
        headers=headers,
    )
    assert listing_resp.status_code == 200
    listing = ListingOut(**listing_resp.json())

    token = create_qr_token(listing.id, require_consent=False)

    resolve_resp = client.get(f"/admin/q/{token}", headers=headers)
    assert resolve_resp.status_code in (302, 303, 307)
    location = resolve_resp.headers.get("location")
    assert location and location.startswith("https://web.mrhost.top/public/listings/")
    assert location.endswith(f"/public/listings/{listing.id}")
