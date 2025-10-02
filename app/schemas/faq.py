from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class FAQTranslationBase(BaseModel):
    language_code: str
    question: str
    answer: str


class FAQTranslationCreate(FAQTranslationBase):
    pass


class FAQBase(BaseModel):
    listing_id: int
    is_active: bool = True


class FAQCreate(FAQBase):
    translations: list[FAQTranslationCreate]


class FAQUpdate(BaseModel):
    is_active: Optional[bool] = None
    translations: Optional[list[FAQTranslationCreate]] = None


class FAQTranslationOut(FAQTranslationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class FAQOut(BaseModel):
    id: int
    listing_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    translations: list[FAQTranslationOut]

    class Config:
        orm_mode = True
