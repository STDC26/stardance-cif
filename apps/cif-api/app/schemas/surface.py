from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any
from app.models.surface import SurfaceStatus
from app.models.component import ComponentType
from app.schemas.cast_payload import CastPayload
from app.services.execution_state import ExecutionState


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


class OperatorVisibility(BaseModel):
    """
    SVS — State Visible Surface.
    Operator sees decision usability signals only.
    Internal scoring stays internal.

    DRJ ruling P2-G4: Expose decision usability signals only.
    Excluded: full HCTS scores, raw scoring vectors, internal decision detail.
    """
    pla_band: str
    confidence_sufficient: bool
    review_required: bool


class ResolvedSurface(BaseModel):
    surface_id: str
    surface_version_id: str
    name: str
    status: str
    sections: list[dict[str, Any]]
    components: list[ResolvedComponent]
    cast_payload: CastPayload                          # Required — no execution without this
    # LIC — Loop Integrity Contract fields (all required — DRJ 2026-04-03)
    cycle_id: str
    trace_id: str
    cast_id: str
    produced_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    # Attribution split — CIF renders, FORGE executes (FQ-5 DRJ 2026-04-03)
    rendered_by: str = "CIF"
    executed_by: str | None = None
    # IMS execution state — FORGE-owned (DRJ P2-G2)
    execution_state: ExecutionState = ExecutionState.IDLE
    recovery_owner: str = "FORGE"
    # SVS operator surface — decision usability signals only (DRJ P2-G4)
    operator_visibility: OperatorVisibility | None = None


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
