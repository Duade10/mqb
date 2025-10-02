from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_admin_login(client: TestClient, admin_user) -> None:
    response = client.post(
        "/admin/auth/token",
        data={"username": "admin", "password": "secret"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_admin_protected_route_requires_token(client: TestClient, db_session: Session, admin_user):
    response = client.post(
        "/admin/listings",
        json={"name": "Test", "slug": "test"},
    )
    assert response.status_code == 401


def test_admin_create_listing_with_token(client: TestClient, db_session: Session, admin_user):
    token_resp = client.post(
        "/admin/auth/token",
        data={"username": "admin", "password": "secret"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = token_resp.json()["access_token"]
    response = client.post(
        "/admin/listings",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Listing", "slug": "listing"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Listing"
