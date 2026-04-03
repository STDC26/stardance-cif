from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any
from app.models.surface import SurfaceStatus
from app.models.component import ComponentType


class ComponentConfigIn(BaseModel):
    component_type: ComponentType
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class SectionIn(BaseModel):
    section_id: str
    components: list[ComponentConfigIn]


class SurfaceCreateIn(BaseModel):
    name: str
    description: str | None = None
    type: str
    sections: list[SectionIn] = Field(default_factory=list)


class ResolvedComponent(BaseModel):
    component_id: str
    component_type: ComponentType
    name: str
    section_id: str
    position: int
    config: dict[str, Any]


class ResolvedSurface(BaseModel):
    surface_id: str
    surface_version_id: str
    name: str
    status: str
    sections: list[dict[str, Any]]
    components: list[ResolvedComponent]
    # LIC — Loop Integrity Contract fields
    cycle_id: str | None = None
    trace_id: str | None = None
    produced_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    producer: str = "CIF"


class SurfaceOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    type: str
    status: str
    created_at: datetime
    produced_by: str = "CIF"
    schema_version: str = "1.0.0"

    model_config = {"from_attributes": True}
