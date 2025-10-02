from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import FAQ, FAQTranslation, Listing, Tutorial, TutorialTranslation

router = APIRouter()


def _with_language_fallback(
    db: Session, translation_model, foreign_key: str, entity_ids: list[int], language: str
):
    if not entity_ids:
        return []
    translations = (
        db.query(translation_model)
        .filter(
            getattr(translation_model, foreign_key).in_(entity_ids),
            translation_model.language_code == language,
        )
        .all()
    )
    if len(translations) != len(entity_ids):
        missing_ids = {id_: True for id_ in entity_ids}
        for tr in translations:
            missing_ids.pop(getattr(tr, foreign_key), None)
        if missing_ids:
            fallback = (
                db.query(translation_model)
                .filter(
                    getattr(translation_model, foreign_key).in_(missing_ids.keys()),
                    translation_model.language_code == "en",
                )
                .all()
            )
            translations.extend(fallback)
    return translations


@router.get("/public/listings/{listing_id}/faqs", tags=["Public"])
def get_faqs(listing_id: int, language: str = "en", db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    faqs = db.query(FAQ).filter(FAQ.listing_id == listing_id, FAQ.is_active.is_(True)).all()
    ids = [faq.id for faq in faqs]
    translations = _with_language_fallback(db, FAQTranslation, "faq_id", ids, language)
    translation_map = {}
    for translation in translations:
        translation_map.setdefault(getattr(translation, "faq_id"), translation)
    data = []
    for faq in faqs:
        tr = translation_map.get(faq.id)
        if not tr:
            continue
        data.append(
            {
                "id": faq.id,
                "question": tr.question,
                "answer": tr.answer,
                "language_code": tr.language_code,
            }
        )
    return {"items": data}


@router.get("/public/listings/{listing_id}/tutorials", tags=["Public"])
def get_tutorials(listing_id: int, language: str = "en", db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    tutorials = (
        db.query(Tutorial).filter(Tutorial.listing_id == listing_id, Tutorial.is_active.is_(True)).all()
    )
    ids = [tutorial.id for tutorial in tutorials]
    translations = _with_language_fallback(db, TutorialTranslation, "tutorial_id", ids, language)
    translation_map = {}
    for translation in translations:
        translation_map.setdefault(getattr(translation, "tutorial_id"), translation)
    data = []
    for tutorial in tutorials:
        tr = translation_map.get(tutorial.id)
        if not tr:
            continue
        data.append(
            {
                "id": tutorial.id,
                "title": tr.title,
                "description": tr.description,
                "video_url": tr.video_url,
                "thumbnail_url": tr.thumbnail_url,
                "language_code": tr.language_code,
            }
        )
    return {"items": data}
