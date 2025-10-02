from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)

    faqs = relationship("FAQ", back_populates="listing", cascade="all, delete-orphan")
    tutorials = relationship("Tutorial", back_populates="listing", cascade="all, delete-orphan")
    consent_templates = relationship(
        "ConsentTemplate", back_populates="listing", cascade="all, delete-orphan"
    )


class ConsentTemplateStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ConsentTemplate(Base, TimestampMixin):
    __tablename__ = "consent_templates"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default=ConsentTemplateStatusEnum.DRAFT.value)
    published_at = Column(DateTime(timezone=True), nullable=True)

    listing = relationship("Listing", back_populates="consent_templates")
    translations = relationship(
        "ConsentTemplateTranslation",
        back_populates="template",
        cascade="all, delete-orphan",
    )
    logs = relationship("ConsentLog", back_populates="template")

    __table_args__ = (UniqueConstraint("listing_id", "version", name="uq_template_version"),)


class ConsentTemplateTranslation(Base, TimestampMixin):
    __tablename__ = "consent_template_translations"

    id = Column(Integer, primary_key=True)
    template_id = Column(
        Integer, ForeignKey("consent_templates.id", ondelete="CASCADE"), nullable=False
    )
    language_code = Column(String(10), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    template = relationship("ConsentTemplate", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("template_id", "language_code", name="uq_template_language"),
    )


class FAQ(Base, TimestampMixin):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    listing = relationship("Listing", back_populates="faqs")
    translations = relationship(
        "FAQTranslation", back_populates="faq", cascade="all, delete-orphan"
    )


class FAQTranslation(Base, TimestampMixin):
    __tablename__ = "faq_translations"

    id = Column(Integer, primary_key=True)
    faq_id = Column(Integer, ForeignKey("faqs.id", ondelete="CASCADE"), nullable=False)
    language_code = Column(String(10), nullable=False)
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)

    faq = relationship("FAQ", back_populates="translations")

    __table_args__ = (UniqueConstraint("faq_id", "language_code", name="uq_faq_language"),)


class Tutorial(Base, TimestampMixin):
    __tablename__ = "tutorials"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    listing = relationship("Listing", back_populates="tutorials")
    translations = relationship(
        "TutorialTranslation", back_populates="tutorial", cascade="all, delete-orphan"
    )


class TutorialTranslation(Base, TimestampMixin):
    __tablename__ = "tutorial_translations"

    id = Column(Integer, primary_key=True)
    tutorial_id = Column(
        Integer, ForeignKey("tutorials.id", ondelete="CASCADE"), nullable=False
    )
    language_code = Column(String(10), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)

    tutorial = relationship("Tutorial", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("tutorial_id", "language_code", name="uq_tutorial_language"),
    )


class ConsentLog(Base, TimestampMixin):
    __tablename__ = "consent_logs"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    template_id = Column(
        Integer, ForeignKey("consent_templates.id", ondelete="SET NULL"), nullable=True
    )
    template_version = Column(Integer, nullable=False)
    language_code = Column(String(10), nullable=False)
    decision = Column(String(10), nullable=False)
    ip_address = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)

    template = relationship("ConsentTemplate", back_populates="logs")


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
