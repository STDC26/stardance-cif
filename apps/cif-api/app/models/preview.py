"""Preview + Review — asset-agnostic approval gate (TCE-10).

A preview token references any CIF asset (conversion_surface or qds) and
carries its own review lifecycle: pending → approved | rejected. The token
itself is the authorization for the public GET / review endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PreviewToken(Base):
    __tablename__ = "preview_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    preview_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    review_state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
