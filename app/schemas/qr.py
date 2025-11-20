from pydantic import BaseModel


class ListingQRCreate(BaseModel):
    require_consent: bool = True


class ListingQRTokenOut(BaseModel):
    token: str
    require_consent: bool
