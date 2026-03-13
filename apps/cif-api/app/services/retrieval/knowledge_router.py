"""
CIF Knowledge Router — Phase-6 Sprint-3

Coordinates retrieval across all indexes based on request scope.
Assembles raw context data for the context builder.
READ-ONLY.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval.asset_index import get_asset_context
from app.services.retrieval.experiment_index import get_experiment_context
from app.services.retrieval.signal_index import get_signal_context
from app.services.retrieval.qds_index import get_qds_context

logger = logging.getLogger(__name__)


async def route_retrieval(
    db: AsyncSession,
    asset_id: Optional[UUID] = None,
    experiment_id: Optional[UUID] = None,
    qds_asset_id: Optional[UUID] = None,
    slug: Optional[str] = None,
    include_signals: bool = True,
    include_experiment: bool = True,
    include_qds: bool = False,
) -> dict:
    """
    Routes retrieval requests to appropriate indexes.
    Returns a raw context dict containing all retrieved data.

    Args:
        db:                 AsyncSession
        asset_id:           Optional surface asset UUID
        experiment_id:      Optional experiment UUID
        qds_asset_id:       Optional QDS asset UUID
        slug:               Optional slug (resolves asset or QDS)
        include_signals:    Whether to fetch signal aggregates
        include_experiment: Whether to fetch experiment context
        include_qds:        Whether to fetch QDS structure

    Returns:
        dict with keys: asset, experiment, signals, qds
        Empty sub-dicts for sections not requested or not found.
    """
    context = {
        "asset": {},
        "experiment": {},
        "signals": {},
        "qds": {},
    }

    # Asset context
    if asset_id or slug:
        context["asset"] = await get_asset_context(
            db=db,
            asset_id=asset_id,
            slug=slug,
        )
        logger.debug("knowledge_router: asset context retrieved")

    # Signal context — requires resolved asset_id
    resolved_asset_id = asset_id or (
        UUID(context["asset"]["asset_id"])
        if context["asset"].get("asset_id") else None
    )
    if include_signals and resolved_asset_id:
        context["signals"] = await get_signal_context(
            db=db,
            asset_id=resolved_asset_id,
        )
        logger.debug("knowledge_router: signal context retrieved")

    # Experiment context
    if include_experiment and (experiment_id or resolved_asset_id):
        context["experiment"] = await get_experiment_context(
            db=db,
            experiment_id=experiment_id,
            asset_id=resolved_asset_id,
        )
        logger.debug("knowledge_router: experiment context retrieved")

    # QDS context
    if include_qds and (qds_asset_id or slug):
        context["qds"] = await get_qds_context(
            db=db,
            qds_asset_id=qds_asset_id,
            slug=slug,
        )
        logger.debug("knowledge_router: QDS context retrieved")

    return context
