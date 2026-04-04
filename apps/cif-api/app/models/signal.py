from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, func, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum

class EventType(str, enum.Enum):
    surface_view = "surface_view"
    surface_engaged = "surface_engaged"
    component_impression = "component_impression"
    component_click = "component_click"
    form_start = "form_start"
    form_submit = "form_submit"
    diagnostic_start = "diagnostic_start"
    diagnostic_complete = "diagnostic_complete"
    offer_view = "offer_view"
    conversion = "conversion"
    step_view = "step_view"
    answer_submitted = "answer_submitted"
    branch_selected = "branch_selected"
    qualification_result = "qualification_result"

class SignalEvent(Base):
    __tablename__ = "signal_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surface_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("experiments.id"), index=True)
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="eventtype"), nullable=False
    )
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

