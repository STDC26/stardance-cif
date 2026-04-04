"""
CIF /render endpoint — FORGE Executor integration surface.

Attribution split (FQ-5 DRJ 2026-04-03):
  CIF renders → rendered_by = "CIF"
  FORGE executes → executed_by set by Executor at runtime

Lineage headers X-Cast-ID, X-Cycle-ID are echoed in the response
so FORGE Executor can trace the full render round-trip.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class RenderRequest(BaseModel):
    surface_id: str
    render_config: dict[str, Any] = Field(default_factory=dict)


class RenderResponse(BaseModel):
    surface_id: str
    rendered_by: str = "CIF"
    render_status: str = "complete"
    cast_id: Optional[str] = None
    cycle_id: Optional[str] = None
    rendered_content: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "1.0.0"


@router.post("/render", response_model=RenderResponse)
async def render(request: Request, body: RenderRequest) -> RenderResponse:
    cast_id = request.headers.get("X-Cast-ID")
    cycle_id = request.headers.get("X-Cycle-ID")
    executed_by = request.headers.get("X-Executed-By", "FORGE")

    logger.info(
        "render: surface_id=%s cast_id=%s cycle_id=%s rendered_by=CIF executed_by=%s",
        body.surface_id,
        cast_id,
        cycle_id,
        executed_by,
    )

    return RenderResponse(
        surface_id=body.surface_id,
        rendered_by="CIF",
        render_status="complete",
        cast_id=cast_id,
        cycle_id=cycle_id,
        rendered_content={},
        schema_version="1.0.0",
    )
