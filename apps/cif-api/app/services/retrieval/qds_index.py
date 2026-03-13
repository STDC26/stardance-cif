"""
CIF QDS Index — Phase-6 Sprint-3

Retrieves QDS flow structure, steps, and outcome mappings.
Queries: qds_assets, qds_versions, qds_flows, qds_steps,
         qds_outcomes, qds_sessions tables.
READ-ONLY.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qds import (
    QDSAsset,
    QDSVersion,
    QDSFlow,
    QDSStep,
    QDSOutcome,
    QDSSession,
)

logger = logging.getLogger(__name__)


async def get_qds_context(
    db: AsyncSession,
    qds_asset_id: Optional[UUID] = None,
    slug: Optional[str] = None,
) -> dict:
    """
    Returns QDS flow structure including steps, outcomes,
    and session completion metrics.
    """
    try:
        # Resolve QDS asset
        if qds_asset_id:
            result = await db.execute(
                select(QDSAsset).where(QDSAsset.id == qds_asset_id)
            )
        elif slug:
            result = await db.execute(
                select(QDSAsset).where(QDSAsset.slug == slug)
            )
        else:
            return {}

        qds_asset = result.scalar_one_or_none()
        if not qds_asset:
            return {}

        # Get latest version
        version_result = await db.execute(
            select(QDSVersion)
            .where(QDSVersion.asset_id == qds_asset.id)
            .order_by(desc(QDSVersion.created_at))
            .limit(1)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            return {"qds_asset_id": str(qds_asset.id),
                    "name": qds_asset.name, "flow": None}

        # Get flow for this version
        flow_result = await db.execute(
            select(QDSFlow)
            .where(QDSFlow.version_id == version.id)
            .limit(1)
        )
        flow = flow_result.scalar_one_or_none()
        if not flow:
            return {"qds_asset_id": str(qds_asset.id),
                    "name": qds_asset.name, "flow": None}

        # Get steps
        steps_result = await db.execute(
            select(QDSStep)
            .where(QDSStep.flow_id == flow.id)
            .order_by(QDSStep.position)
        )
        steps = steps_result.scalars().all()

        # Get outcomes
        outcomes_result = await db.execute(
            select(QDSOutcome)
            .where(QDSOutcome.flow_id == flow.id)
        )
        outcomes = outcomes_result.scalars().all()

        # Get session completion stats
        session_stats = await db.execute(
            select(
                QDSSession.status,
                func.count(QDSSession.id).label("count"),
            )
            .where(QDSSession.asset_id == qds_asset.id)
            .group_by(QDSSession.status)
        )
        session_summary = {
            row.status.value
            if hasattr(row.status, "value") else str(row.status):
            row.count for row in session_stats
        }

        return {
            "qds_asset_id": str(qds_asset.id),
            "name": qds_asset.name,
            "slug": qds_asset.slug,
            "flow_id": str(flow.id),
            "step_count": len(steps),
            "steps": [
                {
                    "position": s.position,
                    "step_type": s.step_type.value
                    if hasattr(s.step_type, "value") else str(s.step_type),
                    "title": s.title,
                }
                for s in steps
            ],
            "outcome_count": len(outcomes),
            "session_summary": session_summary,
            "completion_rate": round(
                session_summary.get("completed", 0) /
                max(sum(session_summary.values()), 1) * 100, 1
            ),
        }

    except Exception as e:
        logger.error("qds_index.get_qds_context error: %s", str(e))
        return {"error": str(e)}
