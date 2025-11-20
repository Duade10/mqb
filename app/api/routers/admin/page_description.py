from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import PageDescription, PageDescriptionTranslation
from app.schemas.page_description import (
    PageDescriptionCreate,
    PageDescriptionOut,
    PageDescriptionUpdate,
)

router = APIRouter(dependencies=[Depends(get_current_admin)])


def _sync_page_description_translations(
    description: PageDescription, translations: list[dict], db: Session
) -> None:
    existing = {tr.language_code: tr for tr in description.translations}
    incoming_codes = set()
    for translation in translations:
        code = translation["language_code"].lower()
        incoming_codes.add(code)
        if code in existing:
            existing[code].body = translation["body"]
        else:
            db.add(
                PageDescriptionTranslation(
                    page_description=description,
                    language_code=code,
                    body=translation["body"],
                )
            )
    for code, translation in existing.items():
        if code not in incoming_codes:
            db.delete(translation)


@router.post("/admin/page-descriptions", response_model=PageDescriptionOut, tags=["Admin"])
def create_page_description(
    payload: PageDescriptionCreate, db: Session = Depends(get_db)
) -> PageDescriptionOut:
    description = PageDescription(
        listing_id=payload.listing_id, is_active=payload.is_active
    )
    db.add(description)
    db.flush()
    _sync_page_description_translations(
        description, [t.dict() for t in payload.translations], db
    )
    db.commit()
    db.refresh(description)
    return description


@router.put(
    "/admin/page-descriptions/{description_id}",
    response_model=PageDescriptionOut,
    tags=["Admin"],
)
def update_page_description(
    description_id: int, payload: PageDescriptionUpdate, db: Session = Depends(get_db)
) -> PageDescriptionOut:
    description = (
        db.query(PageDescription).filter(PageDescription.id == description_id).first()
    )
    if not description:
        raise HTTPException(status_code=404, detail="Page description not found")
    if payload.is_active is not None:
        description.is_active = payload.is_active
    if payload.translations is not None:
        _sync_page_description_translations(
            description, [t.dict() for t in payload.translations], db
        )
    db.add(description)
    db.commit()
    db.refresh(description)
    return description


@router.get(
    "/admin/listings/{listing_id}/page-descriptions",
    response_model=list[PageDescriptionOut],
    tags=["Admin"],
)
def list_page_descriptions(
    listing_id: int, db: Session = Depends(get_db)
) -> list[PageDescriptionOut]:
    return (
        db.query(PageDescription)
        .filter(PageDescription.listing_id == listing_id)
        .order_by(PageDescription.created_at.desc())
        .all()
    )


@router.delete("/admin/page-descriptions/{description_id}", tags=["Admin"])
def delete_page_description(description_id: int, db: Session = Depends(get_db)):
    description = (
        db.query(PageDescription).filter(PageDescription.id == description_id).first()
    )
    if not description:
        raise HTTPException(status_code=404, detail="Page description not found")
    db.delete(description)
    db.commit()
    return {"status": "deleted"}
