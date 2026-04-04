from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class DecisionExplanationSummary(BaseModel):
    """Operator-visible summarized form of decision explanation."""
    primary_reason: str
    pla_band: str
    gating_traits: list[str] = Field(default_factory=list)
    confidence_sufficient: bool
    review_required: bool


class CastPayload(BaseModel):
    """
    CAST decision traceability contract.
    Required on every FORGE execution. No cast_payload = no execution.

    DRJ ruling 2026-04-03:
    - cast_id required (no optional execution paths)
    - cycle_id required (loop traceability)
    - decision_explanation_summary operator-visible
    - executed_by always FORGE
    """
    cast_id: str
    cycle_id: str
    trace_id: str
    pla_band: str
    decision_explanation_summary: DecisionExplanationSummary
    executed_by: str = "FORGE"
    schema_version: str = "1.0.0"
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
