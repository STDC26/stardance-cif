from pydantic import BaseModel, Field
from uuid import UUID
from typing import Any
from app.models.signal import EventType


class SignalEventIn(BaseModel):
    event_type: EventType
    surface_id: UUID
    surface_version_id: UUID | None = None
    experiment_id: UUID | None = None
    session_id: str | None = None
    component_id: str | None = None
    component_type: str | None = None
    event_data: dict[str, Any] = Field(default_factory=dict)


class SignalEventOut(BaseModel):
    id: UUID
    event_type: EventType
    surface_id: UUID
    session_id: str | None
    created_at: str

    model_config = {"from_attributes": True}
