"""
Asset model — reflects the existing 'assets' table in the database.
This table stores generic asset references (component assets, media, etc.)
and is referenced by experiments, signal_aggregates, and insight_reports.
"""

import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    url = Column(String(2048), nullable=False)
    asset_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
