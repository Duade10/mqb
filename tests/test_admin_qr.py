from urllib.parse import urlparse, parse_qs

from sqlalchemy.orm import Session

from app.models import AdminRoleEnum, AdminUser
from app.schemas.listing import ListingOut
from app.utils.security import get_password_hash
from tests.conftest import SimpleTestClient
from tests.test_admin_auth import login


def test_admin_can_generate_listing_qr_link(
    client: SimpleTestClient, db_session: Session
) -> None:
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

    qr_resp = client.get(f"/admin/listings/{listing.id}/qr", headers=headers)
    assert qr_resp.status_code in (302, 303, 307)
    location = qr_resp.headers.get("location")
    assert location and location.startswith("https://api.qrserver.com/v1/create-qr-code/")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert "data" in params
    assert params["data"][0].endswith(f"/public/listings/{listing.id}/consent")
