import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum


class DeploymentEnvironment(str, enum.Enum):
    preview = "preview"
    staging = "staging"
    production = "production"


class DeploymentStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    inactive = "inactive"
    failed = "failed"


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surface_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("surfaces.id"), nullable=False, index=True)
    surface_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("surface_versions.id"), nullable=False, index=True)
    environment: Mapped[DeploymentEnvironment] = mapped_column(
        SAEnum(DeploymentEnvironment, name="deploymentenvironment"), nullable=False
    )
    status: Mapped[DeploymentStatus] = mapped_column(
        SAEnum(DeploymentStatus, name="deploymentstatus"), nullable=False, default=DeploymentStatus.pending
    )
    deployed_by: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    surface: Mapped["Surface"] = relationship(back_populates="deployments")
    surface_version: Mapped["SurfaceVersion"] = relationship(back_populates="deployments")
