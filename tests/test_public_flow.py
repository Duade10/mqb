from datetime import datetime

import jwt
import pytest
import uuid

from sqlalchemy.orm import Session

from tests.conftest import SimpleTestClient

from app.core.config import get_settings
from app.models import (
    ConsentLog,
    ConsentTemplate,
    ConsentTemplateTranslation,
    FAQ,
    FAQTranslation,
    Listing,
    PageDescription,
    PageDescriptionTranslation,
    Tutorial,
    TutorialTranslation,
)
from app.services.qr import create_qr_token, decode_qr_token

settings = get_settings()


def _create_listing(db: Session) -> Listing:
    slug = f"test-listing-{uuid.uuid4().hex[:8]}"
    listing = Listing(name="Test Listing", slug=slug)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def _create_published_consent(db: Session, listing: Listing) -> ConsentTemplate:
    template = ConsentTemplate(listing_id=listing.id, version=1, status="published")
    db.add(template)
    db.flush()
    translation_en = ConsentTemplateTranslation(
        template=template,
        language_code="en",
        title="Consent",
        body="English body",
    )
    translation_es = ConsentTemplateTranslation(
        template=template,
        language_code="es",
        title="Consentimiento",
        body="Cuerpo en español",
    )
    db.add_all([translation_en, translation_es])
    db.commit()
    db.refresh(template)
    return template


def _create_guide_content(db: Session, listing: Listing) -> None:
    faq = FAQ(listing_id=listing.id, is_active=True)
    db.add(faq)
    db.flush()
    db.add_all(
        [
            FAQTranslation(
                faq=faq,
                language_code="en",
                question="Q1",
                answer="A1",
                links=[{"label": "Link", "url": "https://example.com"}],
            ),
            FAQTranslation(
                faq=faq,
                language_code="es",
                question="P1",
                answer="R1",
                links=[{"label": "Enlace", "url": "https://example.com/es"}],
            ),
        ]
    )
    tutorial = Tutorial(listing_id=listing.id, is_active=True)
    db.add(tutorial)
    db.flush()
    db.add_all(
        [
            TutorialTranslation(
                tutorial=tutorial,
                language_code="en",
                title="How to",
                description="English",
                video_url="https://example.com/video",
            ),
        ]
    )
    db.commit()


def _create_page_description(db: Session, listing: Listing) -> PageDescription:
    description = PageDescription(listing_id=listing.id, is_active=True)
    db.add(description)
    db.flush()
    db.add_all(
        [
            PageDescriptionTranslation(
                page_description=description,
                language_code="en",
                body="Welcome to the property.",
            ),
            PageDescriptionTranslation(
                page_description=description,
                language_code="es",
                body="Bienvenido a la propiedad.",
            ),
        ]
    )
    db.commit()
    db.refresh(description)
    return description


def test_qr_token_signing_and_validation(db_session: Session):
    listing = _create_listing(db_session)
    token = create_qr_token(listing.id)
    decoded = decode_qr_token(token)
    assert decoded["listing_id"] == listing.id
    assert decoded["require_consent"] is True


def test_consent_submission_with_stale_version(client: SimpleTestClient, db_session: Session):
    listing = _create_listing(db_session)
    template = _create_published_consent(db_session, listing)

    stale_payload = {
        "template_id": template.id,
        "template_version": template.version - 1,
        "language_code": "en",
        "decision": "accept",
        "email": "guest@example.com",
    }
    response = client.post(
        f"/public/listings/{listing.id}/consent",
        json=stale_payload,
    )
    assert response.status_code == 409


def test_consent_submission_success(client: SimpleTestClient, db_session: Session):
    listing = _create_listing(db_session)
    template = _create_published_consent(db_session, listing)
    payload = {
        "template_id": template.id,
        "template_version": template.version,
        "language_code": "en",
        "decision": "accept",
        "email": "guest@example.com",
    }
    response = client.post(
        f"/public/listings/{listing.id}/consent",
        json=payload,
        headers={"user-agent": "pytest"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "accept"
    assert data["email"] == "guest@example.com"
    assert data["ip_address"]
    log = db_session.query(ConsentLog).first()
    assert log is not None
    assert log.template_version == template.version
    assert log.email == "guest@example.com"


def test_faq_and_tutorial_language_fallback(client: SimpleTestClient, db_session: Session):
    listing = _create_listing(db_session)
    _create_published_consent(db_session, listing)
    _create_guide_content(db_session, listing)
    _create_page_description(db_session, listing)

    faq_response = client.get(f"/public/listings/{listing.id}/faqs", params={"language": "fr"})
    assert faq_response.status_code == 200
    faq_data = faq_response.json()
    assert faq_data["items"][0]["language_code"] == "en"
    assert faq_data["items"][0]["links"][0]["url"] == "https://example.com"

    tutorial_response = client.get(
        f"/public/listings/{listing.id}/tutorials", params={"language": "fr"}
    )
    assert tutorial_response.status_code == 200
    tutorial_data = tutorial_response.json()
    assert tutorial_data["items"][0]["language_code"] == "en"

    description_response = client.get(
        f"/public/listings/{listing.id}/page-descriptions",
        params={"language": "fr"},
    )
    assert description_response.status_code == 200
    description_data = description_response.json()
    assert description_data["items"][0]["language_code"] == "en"
