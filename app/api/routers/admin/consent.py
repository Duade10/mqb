from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import ConsentTemplate, ConsentTemplateStatusEnum, ConsentTemplateTranslation
from app.schemas.consent import ConsentTemplateCreate, ConsentTemplateOut, ConsentTemplateUpdate

router = APIRouter(dependencies=[Depends(get_current_admin)])


def _ensure_translations(translations: list[dict], template: ConsentTemplate, db: Session) -> None:
    existing = {tr.language_code: tr for tr in template.translations}
    incoming_codes = set()
    for translation in translations:
        code = translation["language_code"].lower()
        incoming_codes.add(code)
        if code in existing:
            existing[code].title = translation["title"]
            existing[code].body = translation["body"]
        else:
            db.add(
                ConsentTemplateTranslation(
                    template=template,
                    language_code=code,
                    title=translation["title"],
                    body=translation["body"],
                )
            )
    # remove translations not present anymore
    for code, tr in existing.items():
        if code not in incoming_codes:
            db.delete(tr)


@router.post("/admin/listings/{listing_id}/consent-templates", response_model=ConsentTemplateOut, tags=["Admin"])
def create_consent_template(
    listing_id: int, payload: ConsentTemplateCreate, db: Session = Depends(get_db)
):
    last_template = (
        db.query(ConsentTemplate)
        .filter(ConsentTemplate.listing_id == listing_id)
        .order_by(ConsentTemplate.version.desc())
        .first()
    )
    next_version = 1 if not last_template else last_template.version + 1
    template = ConsentTemplate(listing_id=listing_id, version=next_version, status="draft")
    db.add(template)
    db.flush()
    _ensure_translations([t.dict() for t in payload.translations], template, db)
    db.commit()
    db.refresh(template)
    return template


@router.put("/admin/consent-templates/{template_id}", response_model=ConsentTemplateOut, tags=["Admin"])
def update_consent_template(
    template_id: int, payload: ConsentTemplateUpdate, db: Session = Depends(get_db)
):
    template = db.query(ConsentTemplate).filter(ConsentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if payload.translations is not None:
        _ensure_translations([t.dict() for t in payload.translations], template, db)
    if payload.status:
        if payload.status not in {e.value for e in ConsentTemplateStatusEnum}:
            raise HTTPException(status_code=400, detail="Invalid status")
        template.status = payload.status
        if payload.status == ConsentTemplateStatusEnum.PUBLISHED.value:
            template.published_at = datetime.utcnow()
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/admin/listings/{listing_id}/consent-templates", response_model=list[ConsentTemplateOut], tags=["Admin"])
def list_consent_templates(listing_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ConsentTemplate)
        .filter(ConsentTemplate.listing_id == listing_id)
        .order_by(ConsentTemplate.version.desc())
        .all()
    )
