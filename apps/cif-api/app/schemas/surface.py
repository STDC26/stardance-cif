from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any, Literal, Optional
from app.models.surface import SurfaceStatus
from app.models.component import ComponentType
from app.schemas.cast_payload import CastPayload
from app.services.execution_state import ExecutionState

CQXStage = Literal["context", "outcome", "direction", "conviction", "action"]
CQXIntensity = Literal["low", "medium", "high"]
SCSSPosition = Literal["entry", "mid_funnel", "destination"]


class ComponentConfigIn(BaseModel):
    component_type: ComponentType
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    cqx_stage: CQXStage | None = None
    cqx_intensity: CQXIntensity | None = None


class SectionIn(BaseModel):
    section_id: str
    components: list[ComponentConfigIn]


class SurfaceCreateIn(BaseModel):
    name: str
    description: str | None = None
    type: str
    sections: list[SectionIn] = Field(default_factory=list)
    scss_position: SCSSPosition | None = None
    hcts_target_profile: dict | None = None
    cqx_intensity: CQXIntensity | None = None


class SequencingComponentIn(BaseModel):
    component_type: ComponentType
    cqx_stage: CQXStage | None = None
    cqx_intensity: CQXIntensity | None = None


class SurfaceSequenceIn(BaseModel):
    components: list[SequencingComponentIn]
    scss_position: SCSSPosition = "entry"
    hcts_target_profile: dict | None = None
    cqx_intensity: CQXIntensity = "medium"


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
    cast_payload: Optional[CastPayload] = None         # None on public serve; required for FORGE execution
    # LIC — Loop Integrity Contract fields (required for FORGE execution path — DRJ 2026-04-03)
    cycle_id: Optional[str] = None
    trace_id: Optional[str] = None
    cast_id: Optional[str] = None
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
    current_version_id: UUID | None = None
    name: str
    slug: str
    description: str | None
    type: str
    status: str
    created_at: datetime
    produced_by: str = "CIF"
    schema_version: str = "1.0.0"
    cqx_sequencing: dict | None = None

    model_config = {"from_attributes": True}
