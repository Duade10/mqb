from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Listing
from app.services.qr import decode_qr_token

router = APIRouter()


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
    return RedirectResponse(url=f"/public/listings/{listing.id}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
