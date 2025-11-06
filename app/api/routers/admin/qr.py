from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Listing
from app.services.qr import create_qr_token

router = APIRouter(dependencies=[Depends(get_current_admin)])
settings = get_settings()


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

    base_url = (settings.public_frontend_base_url or "").rstrip("/")
    if base_url:
        listing_url = f"{base_url}/public/listings/{listing.id}"
    else:
        listing_url = str(
            request.url_for("get_consent_template", listing_id=listing.id)
        ).rsplit("/consent", 1)[0]

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data="
        f"{quote(listing_url, safe='')}"
    )
    return RedirectResponse(url=qr_url)
