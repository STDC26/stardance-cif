"""
CIF Insight Router — Phase-6 Sprint-4

Orchestrates all operator intelligence services.
Single entry point for all insight generation.

All insights:
- Use Retrieval Layer for context grounding
- Route through AI Router for inference
- Are READ-ONLY — no platform state changes
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.operator_intelligence.experiment_explainer import (
    explain_experiment,
)
from app.services.operator_intelligence.signal_interpreter import (
    interpret_signals,
)
from app.services.operator_intelligence.asset_analyst import analyze_asset
from app.services.operator_intelligence.diagnostic_analyst import (
    analyze_diagnostic,
)

logger = logging.getLogger(__name__)


class InsightType(str, Enum):
    EXPERIMENT = "experiment"
    SIGNAL = "signal"
    ASSET = "asset"
    DIAGNOSTIC = "diagnostic"


@dataclass
class InsightRequest:
    insight_type: InsightType
    experiment_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    qds_asset_id: Optional[UUID] = None
    slug: Optional[str] = None


async def generate_insight(
    request: InsightRequest,
    db: AsyncSession,
) -> dict:
    """
    Routes insight requests to the appropriate analyst service.

    Args:
        request:    InsightRequest specifying type and identifiers
        db:         AsyncSession

    Returns:
        Insight dict from the appropriate analyst service.
    """
    logger.info(
        "insight_router: generating %s insight",
        request.insight_type.value,
    )

    if request.insight_type == InsightType.EXPERIMENT:
        if not request.experiment_id:
            return {"error": "experiment_id required for EXPERIMENT insight"}
        return await explain_experiment(
            db=db,
            experiment_id=request.experiment_id,
            asset_id=request.asset_id,
        )

    elif request.insight_type == InsightType.SIGNAL:
        if not request.asset_id:
            return {"error": "asset_id required for SIGNAL insight"}
        return await interpret_signals(
            db=db,
            asset_id=request.asset_id,
        )

    elif request.insight_type == InsightType.ASSET:
        if not request.asset_id and not request.slug:
            return {"error": "asset_id or slug required for ASSET insight"}
        return await analyze_asset(
            db=db,
            asset_id=request.asset_id,
            slug=request.slug,
        )

    elif request.insight_type == InsightType.DIAGNOSTIC:
        if not request.qds_asset_id and not request.slug:
            return {"error": "qds_asset_id or slug required for "
                             "DIAGNOSTIC insight"}
        return await analyze_diagnostic(
            db=db,
            qds_asset_id=request.qds_asset_id,
            slug=request.slug,
        )

    else:
        return {"error": f"Unknown insight type: {request.insight_type}"}
