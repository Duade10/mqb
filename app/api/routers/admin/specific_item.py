from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Listing, SpecificItem
from app.schemas.specific_item import SpecificItemOut, SpecificItemUpdate

router = APIRouter(dependencies=[Depends(get_current_admin)])


def _get_listing_or_404(listing_id: int, db: Session) -> Listing:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


def _get_specific_item_or_404(
    listing_id: int, slug: str, db: Session
) -> SpecificItem:
    item = (
        db.query(SpecificItem)
        .filter(
            SpecificItem.listing_id == listing_id,
            SpecificItem.slug == slug,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Specific item not found"
        )
    return item


@router.get("/admin/listings/{listing_id}/items", response_model=list[SpecificItemOut], tags=["Admin"])
def list_specific_items(listing_id: int, db: Session = Depends(get_db)) -> list[SpecificItemOut]:
    _get_listing_or_404(listing_id, db)
    return db.query(SpecificItem).filter(SpecificItem.listing_id == listing_id).all()


@router.get(
    "/admin/listings/{listing_id}/{specific_item}",
    response_model=SpecificItemOut,
    tags=["Admin"],
)
def get_specific_item(
    listing_id: int, specific_item: str, db: Session = Depends(get_db)
) -> SpecificItemOut:
    _get_listing_or_404(listing_id, db)
    return _get_specific_item_or_404(listing_id, specific_item, db)


@router.put(
    "/admin/listings/{listing_id}/{specific_item}",
    response_model=SpecificItemOut,
    tags=["Admin"],
)
def update_specific_item(
    listing_id: int,
    specific_item: str,
    payload: SpecificItemUpdate,
    db: Session = Depends(get_db),
) -> SpecificItemOut:
    _get_listing_or_404(listing_id, db)
    item = _get_specific_item_or_404(listing_id, specific_item, db)

    data = payload.dict(exclude_unset=True)
    if "slug" in data:
        existing = (
            db.query(SpecificItem)
            .filter(
                SpecificItem.listing_id == listing_id,
                SpecificItem.slug == data["slug"],
                SpecificItem.id != item.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A specific item with this slug already exists",
            )

    for field, value in data.items():
        setattr(item, field, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/admin/listings/{listing_id}/{specific_item}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin"],
)
def delete_specific_item(
    listing_id: int, specific_item: str, db: Session = Depends(get_db)
):
    _get_listing_or_404(listing_id, db)
    item = _get_specific_item_or_404(listing_id, specific_item, db)
    db.delete(item)
    db.commit()
    return None
