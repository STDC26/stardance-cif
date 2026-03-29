import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum

class ComponentType(str, enum.Enum):
    hero = "hero"
    text_block = "text_block"
    image = "image"
    video = "video"
    cta = "cta"
    form = "form"
    offer_stack = "offer_stack"
    social_proof = "social_proof"
    testimonial = "testimonial"
    faq = "faq"
    diagnostic_entry = "diagnostic_entry"
    trust_bar = "trust_bar"
    content_grid = "content_grid"

class Component(Base):
    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[ComponentType] = mapped_column(
        SAEnum(ComponentType, name="componenttype"), nullable=False
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    surface_components: Mapped[list["SurfaceComponent"]] = relationship(back_populates="component")


class SurfaceComponent(Base):
    __tablename__ = "surface_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surface_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("surface_versions.id"), nullable=False, index=True)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)
    section_id: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    surface_version: Mapped["SurfaceVersion"] = relationship(back_populates="surface_components")
    component: Mapped["Component"] = relationship(back_populates="surface_components")
