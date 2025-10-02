from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class TutorialTranslationBase(BaseModel):
    language_code: str
    title: str
    description: Optional[str] = None
    video_url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None


class TutorialTranslationCreate(TutorialTranslationBase):
    pass


class TutorialBase(BaseModel):
    listing_id: int
    is_active: bool = True


class TutorialCreate(TutorialBase):
    translations: list[TutorialTranslationCreate]


class TutorialUpdate(BaseModel):
    is_active: Optional[bool] = None
    translations: Optional[list[TutorialTranslationCreate]] = None


class TutorialTranslationOut(TutorialTranslationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TutorialOut(BaseModel):
    id: int
    listing_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    translations: list[TutorialTranslationOut]

    class Config:
        orm_mode = True
