"""
CIF Copilot API — Phase-6 Sprint-5

Exposes AI-assisted draft generation endpoints.
All endpoints return drafts with status="draft".
No platform state changes — drafts are returned, not persisted.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.db.session import get_db
from app.services.copilot import (
    generate_draft,
    CopilotRequest,
    CopilotAction,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


class SurfaceDraftBody(BaseModel):
    slug: Optional[str] = None
    asset_id: Optional[UUID] = None
    brief: Optional[str] = None


class QDSDraftBody(BaseModel):
    slug: Optional[str] = None
    qds_asset_id: Optional[UUID] = None
    brief: Optional[str] = None


class VariantBody(BaseModel):
    experiment_id: UUID
    asset_id: Optional[UUID] = None
    brief: Optional[str] = None


class ExperimentRecBody(BaseModel):
    slug: Optional[str] = None
    asset_id: Optional[UUID] = None
    brief: Optional[str] = None


@router.get("/health")
async def copilot_health(_: str = Depends(require_api_key)):
    """Confirms Copilot services are available."""
    return {
        "status": "ok",
        "layer": "copilot",
        "services": [
            "surface_draft_generator",
            "qds_draft_generator",
            "variant_generator",
            "experiment_recommender",
        ],
        "copilot_router": "active",
    }


@router.post("/surface-draft")
async def surface_draft(
    body: SurfaceDraftBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an AI-assisted surface draft.
    Optionally grounded in existing asset context.
    """
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.SURFACE_DRAFT,
            slug=body.slug,
            asset_id=body.asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/qds-draft")
async def qds_draft(
    body: QDSDraftBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an AI-assisted QDS diagnostic flow draft.
    Optionally grounded in existing QDS context.
    """
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.QDS_DRAFT,
            slug=body.slug,
            qds_asset_id=body.qds_asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/variants")
async def variant_suggestions(
    body: VariantBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates AI-assisted variant suggestions for an experiment.
    Grounded in existing experiment and signal context.
    """
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.VARIANT_SUGGESTION,
            experiment_id=body.experiment_id,
            asset_id=body.asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/experiment-recommendations")
async def experiment_recommendations(
    body: ExperimentRecBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates AI-assisted experiment recommendations for an asset.
    Grounded in asset performance, signals, and existing experiments.
    """
    if not body.slug and not body.asset_id:
        raise HTTPException(
            status_code=422,
            detail="slug or asset_id required",
        )
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.EXPERIMENT_RECOMMENDATION,
            slug=body.slug,
            asset_id=body.asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
