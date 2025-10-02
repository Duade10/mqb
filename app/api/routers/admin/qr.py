from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Listing
from app.services.qr import create_qr_token

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.post("/admin/listings/{listing_id}/qr", tags=["Admin"])
def generate_listing_qr(listing_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    token = create_qr_token(listing.id)
    return {"token": token}
