from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import FAQ, FAQTranslation
from app.schemas.faq import FAQCreate, FAQOut, FAQUpdate

router = APIRouter(dependencies=[Depends(get_current_admin)])


def _sync_faq_translations(faq: FAQ, translations: list[dict], db: Session) -> None:
    existing = {tr.language_code: tr for tr in faq.translations}
    incoming_codes = set()
    for translation in translations:
        code = translation["language_code"].lower()
        incoming_codes.add(code)
        if code in existing:
            existing[code].question = translation["question"]
            existing[code].answer = translation["answer"]
            existing[code].links = translation.get("links")
        else:
            db.add(
                FAQTranslation(
                    faq=faq,
                    language_code=code,
                    question=translation["question"],
                    answer=translation["answer"],
                    links=translation.get("links"),
                )
            )
    for code, translation in existing.items():
        if code not in incoming_codes:
            db.delete(translation)


@router.post("/admin/faqs", response_model=FAQOut, tags=["Admin"])
def create_faq(payload: FAQCreate, db: Session = Depends(get_db)) -> FAQOut:
    faq = FAQ(
        listing_id=payload.listing_id,
        specific_item=payload.specific_item,
        is_active=payload.is_active,
    )
    db.add(faq)
    db.flush()
    _sync_faq_translations(faq, [t.dict() for t in payload.translations], db)
    db.commit()
    db.refresh(faq)
    return faq


@router.put("/admin/faqs/{faq_id}", response_model=FAQOut, tags=["Admin"])
def update_faq(faq_id: int, payload: FAQUpdate, db: Session = Depends(get_db)) -> FAQOut:
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    if payload.is_active is not None:
        faq.is_active = payload.is_active
    if payload.specific_item is not None:
        faq.specific_item = payload.specific_item
    if payload.translations is not None:
        _sync_faq_translations(faq, [t.dict() for t in payload.translations], db)
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return faq


def _list_faqs(listing_id: int, specific_item: str | None, db: Session) -> list[FAQOut]:
    query = db.query(FAQ).filter(FAQ.listing_id == listing_id)
    if specific_item is None:
        query = query.filter(FAQ.specific_item.is_(None))
    else:
        query = query.filter(FAQ.specific_item == specific_item)
    return query.all()


@router.get("/admin/listings/{listing_id}/faqs", response_model=list[FAQOut], tags=["Admin"])
def list_faqs(listing_id: int, db: Session = Depends(get_db)) -> list[FAQOut]:
    return _list_faqs(listing_id, None, db)


@router.get(
    "/admin/listings/{listing_id}/{specific_item}/faqs",
    response_model=list[FAQOut],
    tags=["Admin"],
)
def list_specific_faqs(
    listing_id: int, specific_item: str, db: Session = Depends(get_db)
) -> list[FAQOut]:
    return _list_faqs(listing_id, specific_item, db)


@router.delete("/admin/faqs/{faq_id}", tags=["Admin"])
def delete_faq(faq_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    db.delete(faq)
    db.commit()
    return {"status": "deleted"}
