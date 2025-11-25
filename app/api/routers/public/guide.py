from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    FAQ,
    FAQTranslation,
    Listing,
    PageDescription,
    PageDescriptionTranslation,
    Tutorial,
    TutorialTranslation,
)

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
    listing = _get_listing(listing_id, db)
    faqs = (
        db.query(FAQ)
        .filter(
            FAQ.listing_id == listing.id,
            FAQ.is_active.is_(True),
            FAQ.specific_item.is_(None),
        )
        .all()
    )
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
                "links": tr.links,
                "language_code": tr.language_code,
            }
        )
    return {"items": data}


@router.get(
    "/public/listings/{listing_id}/{specific_item}/faqs",
    tags=["Public"],
)
def get_specific_faqs(
    listing_id: int, specific_item: str, language: str = "en", db: Session = Depends(get_db)
):
    listing = _get_listing(listing_id, db)
    faqs = (
        db.query(FAQ)
        .filter(
            FAQ.listing_id == listing.id,
            FAQ.is_active.is_(True),
            FAQ.specific_item == specific_item,
        )
        .all()
    )
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
                "links": tr.links,
                "language_code": tr.language_code,
            }
        )
    return {"items": data}


@router.get("/public/listings/{listing_id}/tutorials", tags=["Public"])
def get_tutorials(listing_id: int, language: str = "en", db: Session = Depends(get_db)):
    listing = _get_listing(listing_id, db)
    tutorials = (
        db.query(Tutorial)
        .filter(
            Tutorial.listing_id == listing.id,
            Tutorial.is_active.is_(True),
            Tutorial.specific_item.is_(None),
        )
        .all()
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


@router.get(
    "/public/listings/{listing_id}/{specific_item}/tutorials",
    tags=["Public"],
)
def get_specific_tutorials(
    listing_id: int, specific_item: str, language: str = "en", db: Session = Depends(get_db)
):
    listing = _get_listing(listing_id, db)
    tutorials = (
        db.query(Tutorial)
        .filter(
            Tutorial.listing_id == listing.id,
            Tutorial.is_active.is_(True),
            Tutorial.specific_item == specific_item,
        )
        .all()
    )
    ids = [tutorial.id for tutorial in tutorials]
    translations = _with_language_fallback(
        db, TutorialTranslation, "tutorial_id", ids, language
    )
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


@router.get("/public/listings/{listing_id}/page-descriptions", tags=["Public"])
def get_page_descriptions(
    listing_id: int, language: str = "en", db: Session = Depends(get_db)
):
    listing = _get_listing(listing_id, db)
    descriptions = (
        db.query(PageDescription)
        .filter(
            PageDescription.listing_id == listing.id,
            PageDescription.is_active.is_(True),
            PageDescription.specific_item.is_(None),
        )
        .all()
    )
    ids = [description.id for description in descriptions]
    translations = _with_language_fallback(
        db, PageDescriptionTranslation, "page_description_id", ids, language
    )
    translation_map = {}
    for translation in translations:
        translation_map.setdefault(getattr(translation, "page_description_id"), translation)
    data = []
    for description in descriptions:
        tr = translation_map.get(description.id)
        if not tr:
            continue
        data.append(
            {
                "id": description.id,
                "body": tr.body,
                "language_code": tr.language_code,
            }
        )
    return {"items": data}


@router.get(
    "/public/listings/{listing_id}/{specific_item}/page-descriptions",
    tags=["Public"],
)
def get_specific_page_descriptions(
    listing_id: int, specific_item: str, language: str = "en", db: Session = Depends(get_db)
):
    listing = _get_listing(listing_id, db)
    descriptions = (
        db.query(PageDescription)
        .filter(
            PageDescription.listing_id == listing.id,
            PageDescription.is_active.is_(True),
            PageDescription.specific_item == specific_item,
        )
        .all()
    )
    ids = [description.id for description in descriptions]
    translations = _with_language_fallback(
        db, PageDescriptionTranslation, "page_description_id", ids, language
    )
    translation_map = {}
    for translation in translations:
        translation_map.setdefault(getattr(translation, "page_description_id"), translation)
    data = []
    for description in descriptions:
        tr = translation_map.get(description.id)
        if not tr:
            continue
        data.append(
            {
                "id": description.id,
                "body": tr.body,
                "language_code": tr.language_code,
            }
        )
    return {"items": data}


def _get_listing(listing_id: int, db: Session) -> Listing:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
