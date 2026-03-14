"""
CIF Insights API — Phase-6 Sprint-4

Exposes Operator Intelligence endpoints.
All endpoints are READ-ONLY. No platform state changes.
All responses are AI-generated and grounded in retrieval context.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.db.session import get_db
from app.services.operator_intelligence import (
    generate_insight,
    InsightRequest,
    InsightType,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("/health")
async def insights_health(_: str = Depends(require_api_key)):
    """Confirms Operator Intelligence services are available."""
    return {
        "status": "ok",
        "layer": "operator_intelligence",
        "services": [
            "experiment_explainer",
            "signal_interpreter",
            "asset_analyst",
            "diagnostic_analyst",
        ],
        "insight_router": "active",
    }


@router.get("/experiments/{experiment_id}")
async def experiment_insight(
    experiment_id: UUID,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns AI-generated explanation of experiment results.
    Grounded in retrieval context from experiments,
    variants, and signal aggregates.
    """
    result = await generate_insight(
        request=InsightRequest(
            insight_type=InsightType.EXPERIMENT,
            experiment_id=experiment_id,
        ),
        db=db,
    )
    if result.get("error") and not result.get("experiment_summary"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/assets/{slug}")
async def asset_insight(
    slug: str,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns AI-generated performance narrative for an asset.
    Grounded in signal aggregates, experiments, and deployment context.
    """
    result = await generate_insight(
        request=InsightRequest(
            insight_type=InsightType.ASSET,
            slug=slug,
        ),
        db=db,
    )
    if result.get("error") and not result.get("asset_performance_summary"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/qds/{slug}")
async def qds_insight(
    slug: str,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns AI-generated diagnostic flow analysis for a QDS asset.
    Grounded in QDS structure, steps, and session completion data.
    """
    result = await generate_insight(
        request=InsightRequest(
            insight_type=InsightType.DIAGNOSTIC,
            slug=slug,
        ),
        db=db,
    )
    if result.get("error") and not result.get("diagnostic_flow_analysis"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/signals/{asset_id}")
async def signal_insight(
    asset_id: UUID,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns AI-generated signal trend interpretation for an asset.
    Grounded in signal aggregates and event distribution.
    """
    result = await generate_insight(
        request=InsightRequest(
            insight_type=InsightType.SIGNAL,
            asset_id=asset_id,
        ),
        db=db,
    )
    if result.get("error") and not result.get("signal_summary"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
