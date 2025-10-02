from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Listing
from app.schemas.listing import ListingCreate, ListingOut, ListingUpdate

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.post("/admin/listings", response_model=ListingOut, tags=["Admin"])
def create_listing(listing_in: ListingCreate, db: Session = Depends(get_db)) -> ListingOut:
    listing = Listing(name=listing_in.name, slug=listing_in.slug)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/admin/listings", response_model=list[ListingOut], tags=["Admin"])
def list_listings(db: Session = Depends(get_db)) -> list[ListingOut]:
    return db.query(Listing).all()


@router.get("/admin/listings/{listing_id}", response_model=ListingOut, tags=["Admin"])
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> ListingOut:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


@router.put("/admin/listings/{listing_id}", response_model=ListingOut, tags=["Admin"])
def update_listing(
    listing_id: int, listing_in: ListingUpdate, db: Session = Depends(get_db)
) -> ListingOut:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    for field, value in listing_in.dict(exclude_unset=True).items():
        setattr(listing, field, value)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/admin/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    db.delete(listing)
    db.commit()
    return None
