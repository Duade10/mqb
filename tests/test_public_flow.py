from datetime import datetime

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    ConsentLog,
    ConsentTemplate,
    ConsentTemplateTranslation,
    FAQ,
    FAQTranslation,
    Listing,
    Tutorial,
    TutorialTranslation,
)
from app.services.qr import create_qr_token, decode_qr_token

settings = get_settings()


def _create_listing(db: Session) -> Listing:
    listing = Listing(name="Test Listing", slug="test-listing")
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
                faq=faq, language_code="en", question="Q1", answer="A1"
            ),
            FAQTranslation(
                faq=faq, language_code="es", question="P1", answer="R1"
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


def test_qr_token_signing_and_validation(db_session: Session):
    listing = _create_listing(db_session)
    token = create_qr_token(listing.id)
    decoded = decode_qr_token(token)
    assert decoded["listing_id"] == listing.id


def test_consent_submission_with_stale_version(client: TestClient, db_session: Session):
    listing = _create_listing(db_session)
    template = _create_published_consent(db_session, listing)

    stale_payload = {
        "template_id": template.id,
        "template_version": template.version - 1,
        "language_code": "en",
        "decision": "accept",
    }
    response = client.post(
        f"/public/listings/{listing.id}/consent",
        json=stale_payload,
    )
    assert response.status_code == 409


def test_consent_submission_success(client: TestClient, db_session: Session):
    listing = _create_listing(db_session)
    template = _create_published_consent(db_session, listing)
    payload = {
        "template_id": template.id,
        "template_version": template.version,
        "language_code": "en",
        "decision": "accept",
    }
    response = client.post(
        f"/public/listings/{listing.id}/consent",
        json=payload,
        headers={"user-agent": "pytest"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "accept"
    log = db_session.query(ConsentLog).first()
    assert log is not None
    assert log.template_version == template.version


def test_faq_and_tutorial_language_fallback(client: TestClient, db_session: Session):
    listing = _create_listing(db_session)
    _create_published_consent(db_session, listing)
    _create_guide_content(db_session, listing)

    faq_response = client.get(f"/public/listings/{listing.id}/faqs", params={"language": "fr"})
    assert faq_response.status_code == 200
    faq_data = faq_response.json()
    assert faq_data["items"][0]["language_code"] == "en"

    tutorial_response = client.get(
        f"/public/listings/{listing.id}/tutorials", params={"language": "fr"}
    )
    assert tutorial_response.status_code == 200
    tutorial_data = tutorial_response.json()
    assert tutorial_data["items"][0]["language_code"] == "en"
