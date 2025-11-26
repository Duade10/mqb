from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SpecificItemBase(BaseModel):
    name: str
    slug: str


class SpecificItemUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


class SpecificItemOut(SpecificItemBase):
    id: int
    listing_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
