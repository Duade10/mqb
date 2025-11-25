from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Tutorial, TutorialTranslation
from app.schemas.tutorial import TutorialCreate, TutorialOut, TutorialUpdate

router = APIRouter(dependencies=[Depends(get_current_admin)])


def _sync_tutorial_translations(tutorial: Tutorial, translations: list[dict], db: Session) -> None:
    existing = {tr.language_code: tr for tr in tutorial.translations}
    incoming_codes = set()
    for translation in translations:
        code = translation["language_code"].lower()
        incoming_codes.add(code)
        if code in existing:
            existing[code].title = translation["title"]
            existing[code].description = translation.get("description")
            existing[code].video_url = translation["video_url"]
            existing[code].thumbnail_url = translation.get("thumbnail_url")
        else:
            db.add(
                TutorialTranslation(
                    tutorial=tutorial,
                    language_code=code,
                    title=translation["title"],
                    description=translation.get("description"),
                    video_url=translation["video_url"],
                    thumbnail_url=translation.get("thumbnail_url"),
                )
            )
    for code, translation in existing.items():
        if code not in incoming_codes:
            db.delete(translation)


@router.post("/admin/tutorials", response_model=TutorialOut, tags=["Admin"])
def create_tutorial(payload: TutorialCreate, db: Session = Depends(get_db)) -> TutorialOut:
    tutorial = Tutorial(
        listing_id=payload.listing_id,
        specific_item=payload.specific_item,
        is_active=payload.is_active,
    )
    db.add(tutorial)
    db.flush()
    _sync_tutorial_translations(tutorial, [t.dict() for t in payload.translations], db)
    db.commit()
    db.refresh(tutorial)
    return tutorial


@router.put("/admin/tutorials/{tutorial_id}", response_model=TutorialOut, tags=["Admin"])
def update_tutorial(
    tutorial_id: int, payload: TutorialUpdate, db: Session = Depends(get_db)
) -> TutorialOut:
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    if payload.is_active is not None:
        tutorial.is_active = payload.is_active
    if payload.specific_item is not None:
        tutorial.specific_item = payload.specific_item
    if payload.translations is not None:
        _sync_tutorial_translations(tutorial, [t.dict() for t in payload.translations], db)
    db.add(tutorial)
    db.commit()
    db.refresh(tutorial)
    return tutorial


def _list_tutorials(listing_id: int, specific_item: str | None, db: Session) -> list[TutorialOut]:
    query = db.query(Tutorial).filter(Tutorial.listing_id == listing_id)
    if specific_item is None:
        query = query.filter(Tutorial.specific_item.is_(None))
    else:
        query = query.filter(Tutorial.specific_item == specific_item)
    return query.all()


@router.get(
    "/admin/listings/{listing_id}/tutorials", response_model=list[TutorialOut], tags=["Admin"]
)
def list_tutorials(listing_id: int, db: Session = Depends(get_db)) -> list[TutorialOut]:
    return _list_tutorials(listing_id, None, db)


@router.get(
    "/admin/listings/{listing_id}/{specific_item}/tutorials",
    response_model=list[TutorialOut],
    tags=["Admin"],
)
def list_specific_tutorials(
    listing_id: int, specific_item: str, db: Session = Depends(get_db)
) -> list[TutorialOut]:
    return _list_tutorials(listing_id, specific_item, db)


@router.delete("/admin/tutorials/{tutorial_id}", tags=["Admin"])
def delete_tutorial(tutorial_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    db.delete(tutorial)
    db.commit()
    return {"status": "deleted"}
