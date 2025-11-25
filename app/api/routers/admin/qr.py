from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Listing
from app.schemas.qr import ListingQRCreate, ListingQRTokenOut
from app.services.qr import create_qr_token, decode_qr_token

router = APIRouter(dependencies=[Depends(get_current_admin)])
settings = get_settings()


@router.get("/admin/q/{token}", tags=["Admin"])
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


@router.get("/admin/qr", tags=["Admin"])
def generate_qr_from_url(url: str | None = None) -> RedirectResponse:
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A URL parameter is required to generate a QR code",
        )

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data="
        f"{quote(url, safe='')}"
    )
    return RedirectResponse(url=qr_url)


@router.post(
    "/admin/listings/{listing_id}/qr",
    response_model=ListingQRTokenOut,
    tags=["Admin"],
)
def generate_listing_qr(
    listing_id: int, payload: ListingQRCreate, db: Session = Depends(get_db)
) -> ListingQRTokenOut:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    token = create_qr_token(listing.id, require_consent=payload.require_consent)
    return {"token": token, "require_consent": payload.require_consent}


@router.get("/admin/listings/{listing_id}/qr", tags=["Admin"])
def get_listing_qr_image(
    listing_id: int,
    request: Request,
    db: Session = Depends(get_db),
    require_consent: bool = True,
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
    if require_consent:
        listing_url = f"{listing_url}?require_consent=true"

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data="
        f"{quote(listing_url, safe='')}"
    )
    return RedirectResponse(url=qr_url)
