"""
CIF Copilot Router — Phase-6 Sprint-5

Orchestrates all copilot draft generation services.
Single entry point for all AI-assisted draft creation.

All drafts:
- Use Retrieval Layer for context grounding
- Route through AI Router for inference
- Enforce status="draft" governance rule
- Are READ-ONLY — no platform state changes
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.copilot.surface_draft_generator import (
    generate_surface_draft,
)
from app.services.copilot.qds_draft_generator import generate_qds_draft
from app.services.copilot.variant_generator import generate_variants
from app.services.copilot.experiment_recommender import (
    recommend_experiments,
)

logger = logging.getLogger(__name__)


class CopilotAction(str, Enum):
    SURFACE_DRAFT = "surface_draft"
    QDS_DRAFT = "qds_draft"
    VARIANT_SUGGESTION = "variant_suggestion"
    EXPERIMENT_RECOMMENDATION = "experiment_recommendation"


@dataclass
class CopilotRequest:
    action: CopilotAction
    slug: Optional[str] = None
    asset_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    qds_asset_id: Optional[UUID] = None
    brief: Optional[str] = None


async def generate_draft(
    request: CopilotRequest,
    db: AsyncSession,
) -> dict:
    """
    Routes copilot requests to the appropriate draft generator.

    Args:
        request:    CopilotRequest specifying action and identifiers
        db:         AsyncSession

    Returns:
        Draft dict from the appropriate generator service.
    """
    logger.info(
        "copilot_router: generating %s",
        request.action.value,
    )

    if request.action == CopilotAction.SURFACE_DRAFT:
        return await generate_surface_draft(
            db=db,
            slug=request.slug,
            asset_id=request.asset_id,
            brief=request.brief,
        )

    elif request.action == CopilotAction.QDS_DRAFT:
        return await generate_qds_draft(
            db=db,
            slug=request.slug,
            qds_asset_id=request.qds_asset_id,
            brief=request.brief,
        )

    elif request.action == CopilotAction.VARIANT_SUGGESTION:
        if not request.experiment_id:
            return {"error": "experiment_id required for "
                             "VARIANT_SUGGESTION action"}
        return await generate_variants(
            db=db,
            experiment_id=request.experiment_id,
            asset_id=request.asset_id,
            brief=request.brief,
        )

    elif request.action == CopilotAction.EXPERIMENT_RECOMMENDATION:
        if not request.asset_id and not request.slug:
            return {"error": "asset_id or slug required for "
                             "EXPERIMENT_RECOMMENDATION action"}
        return await recommend_experiments(
            db=db,
            slug=request.slug,
            asset_id=request.asset_id,
            brief=request.brief,
        )

    else:
        return {"error": f"Unknown copilot action: {request.action}"}
