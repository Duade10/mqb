import uuid

from sqlalchemy.orm import Session

from tests.conftest import SimpleTestClient
from tests.test_admin_auth import login

from app.models import Listing, SpecificItem


def _create_listing(db: Session) -> Listing:
    listing = Listing(name="Test Listing", slug=f"listing-{uuid.uuid4().hex[:8]}")
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def test_create_specific_item(client: SimpleTestClient, db_session: Session, admin_user) -> None:
    tokens = login(client, admin_user.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    listing = _create_listing(db_session)

    payload = {"name": "Parking", "slug": "parking"}
    response = client.post(
        f"/admin/listings/{listing.id}/items", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["slug"] == payload["slug"]
    assert data["listing_id"] == listing.id

    created = (
        db_session.query(SpecificItem)
        .filter(SpecificItem.listing_id == listing.id, SpecificItem.slug == payload["slug"])
        .first()
    )
    assert created is not None


def test_create_specific_item_duplicate_slug(
    client: SimpleTestClient, db_session: Session, admin_user
) -> None:
    tokens = login(client, admin_user.email, "Secretpass1!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    listing = _create_listing(db_session)

    payload = {"name": "Room A", "slug": "room-a"}
    first_response = client.post(
        f"/admin/listings/{listing.id}/items", json=payload, headers=headers
    )
    assert first_response.status_code == 200

    second_response = client.post(
        f"/admin/listings/{listing.id}/items", json=payload, headers=headers
    )
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "A specific item with this slug already exists"
