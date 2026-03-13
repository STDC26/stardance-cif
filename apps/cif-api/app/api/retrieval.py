"""
CIF Retrieval API — Phase-6 Sprint-3

Exposes retrieval layer health and context inspection endpoints.
Used for testing, debugging, and Sprint-4 operator intelligence.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.db.session import get_db
from app.services.retrieval import build_context, RetrievalRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


class ContextRequest(BaseModel):
    asset_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    qds_asset_id: Optional[UUID] = None
    slug: Optional[str] = None
    include_signals: bool = True
    include_experiment: bool = True
    include_qds: bool = False

    @model_validator(mode="after")
    def require_at_least_one_identifier(self):
        if not any([self.asset_id, self.experiment_id,
                    self.qds_asset_id, self.slug]):
            raise ValueError(
                "At least one of asset_id, experiment_id, "
                "qds_asset_id, or slug is required."
            )
        return self


@router.get("/health")
async def retrieval_health(_: str = Depends(require_api_key)):
    """Confirms retrieval layer is registered and reachable."""
    return {
        "status": "ok",
        "layer": "retrieval",
        "indexes": [
            "asset_index",
            "experiment_index",
            "signal_index",
            "qds_index",
        ],
        "context_builder": "active",
    }


@router.post("/context")
async def get_context(
    body: ContextRequest,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Builds and returns a context bundle for the given request.
    Used to inspect what context the AI router will receive.
    """
    request = RetrievalRequest(
        asset_id=body.asset_id,
        experiment_id=body.experiment_id,
        qds_asset_id=body.qds_asset_id,
        slug=body.slug,
        include_signals=body.include_signals,
        include_experiment=body.include_experiment,
        include_qds=body.include_qds,
    )

    context = await build_context(request=request, db=db)

    return {
        "status": "ok",
        "key_count": len(context),
        "context": context,
    }
