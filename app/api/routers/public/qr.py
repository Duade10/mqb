from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Listing
from app.services.qr import decode_qr_token

router = APIRouter()
settings = get_settings()


@router.get("/q/{token}", tags=["Public"])
def resolve_qr(token: str, db: Session = Depends(get_db)) -> Response:
    try:
        payload = decode_qr_token(token)
    except Exception as exc:  # pragma: no cover - specific errors handled the same
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token") from exc
    listing_id = payload.get("listing_id")
    if not listing_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    base_url = (settings.public_frontend_base_url or "").rstrip("/")
    listing_path = f"/public/listings/{listing.id}"
    if payload.get("require_consent", True):
        listing_path = f"{listing_path}?require_consent=true"
    redirect_url = f"{base_url}{listing_path}" if base_url else listing_path
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
