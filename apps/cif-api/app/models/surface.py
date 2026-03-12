import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum


class SurfaceStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Surface(Base):
    __tablename__ = "surfaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    surface_versions: Mapped[list["SurfaceVersion"]] = relationship(back_populates="surface")
    signal_events: Mapped[list["SignalEvent"]] = relationship(back_populates="surface")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="surface")


class SurfaceVersion(Base):
    __tablename__ = "surface_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surface_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("surfaces.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    surface: Mapped["Surface"] = relationship(back_populates="surface_versions")
    surface_components: Mapped[list["SurfaceComponent"]] = relationship(back_populates="surface_version")
