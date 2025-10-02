from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ListingBase(BaseModel):
    name: str
    slug: str


class ListingCreate(ListingBase):
    pass


class ListingUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


class ListingOut(ListingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
