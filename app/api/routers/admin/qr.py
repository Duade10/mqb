from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
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


@router.get("/admin/listings/{listing_id}/qr", tags=["Admin"])
def get_listing_qr_image(
    listing_id: int, request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    consent_url = request.url_for("get_consent_template", listing_id=listing.id)
    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data="
        f"{quote(str(consent_url), safe='')}"
    )
    return RedirectResponse(url=qr_url)
