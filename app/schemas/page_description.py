from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PageDescriptionTranslationBase(BaseModel):
    language_code: str
    body: str


class PageDescriptionTranslationCreate(PageDescriptionTranslationBase):
    pass


class PageDescriptionBase(BaseModel):
    listing_id: int
    is_active: bool = True


class PageDescriptionCreate(PageDescriptionBase):
    translations: list[PageDescriptionTranslationCreate]


class PageDescriptionUpdate(BaseModel):
    is_active: Optional[bool] = None
    translations: Optional[list[PageDescriptionTranslationCreate]] = None


class PageDescriptionTranslationOut(PageDescriptionTranslationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PageDescriptionOut(BaseModel):
    id: int
    listing_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    translations: list[PageDescriptionTranslationOut]

    class Config:
        orm_mode = True
