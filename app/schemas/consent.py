from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConsentTranslationBase(BaseModel):
    language_code: str
    title: str
    body: str


class ConsentTranslationCreate(ConsentTranslationBase):
    pass


class ConsentTemplateBase(BaseModel):
    listing_id: int


class ConsentTemplateCreate(ConsentTemplateBase):
    translations: list[ConsentTranslationCreate]


class ConsentTemplateUpdate(BaseModel):
    translations: Optional[list[ConsentTranslationCreate]] = None
    status: Optional[str] = None


class ConsentTranslationOut(ConsentTranslationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ConsentTemplateOut(BaseModel):
    id: int
    listing_id: int
    version: int
    status: str
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    translations: list[ConsentTranslationOut]

    class Config:
        orm_mode = True


class ConsentDecisionCreate(BaseModel):
    template_id: int
    template_version: int
    language_code: str
    decision: str


class ConsentDecisionOut(BaseModel):
    id: int
    template_version: int
    decision: str
    language_code: str
    created_at: datetime

    class Config:
        orm_mode = True
