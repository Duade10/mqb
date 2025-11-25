from urllib.parse import parse_qs, urlparse

from tests.conftest import SimpleTestClient


def test_generate_qr_from_url(client: SimpleTestClient) -> None:
    response = client.get("/qr", params={"url": "https://example.com/path?query=1"})

    assert response.status_code in (302, 303, 307)
    location = response.headers.get("location")
    assert location and location.startswith("https://api.qrserver.com/v1/create-qr-code/")

    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert params.get("data") == ["https://example.com/path?query=1"]


def test_generate_qr_from_url_requires_param(client: SimpleTestClient) -> None:
    response = client.get("/qr")

    assert response.status_code == 400
    assert response.json()["detail"] == "A URL parameter is required to generate a QR code"
