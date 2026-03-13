"""
CIF Experiment Index — Phase-6 Sprint-3

Retrieves experiment lifecycle data, variant definitions,
traffic allocation, and results.
Queries: experiments, experiment_variants, experiment_assignments,
         insight_reports tables.
READ-ONLY.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import (
    Experiment,
    ExperimentVariant,
    ExperimentAssignment,
    InsightReport,
)

logger = logging.getLogger(__name__)


async def get_experiment_context(
    db: AsyncSession,
    experiment_id: Optional[UUID] = None,
    asset_id: Optional[UUID] = None,
    limit: int = 1,
) -> dict:
    """
    Returns experiment data including variants and assignment counts.
    If experiment_id provided, returns that experiment.
    If asset_id provided, returns most recent experiment for that asset.
    """
    try:
        if experiment_id:
            result = await db.execute(
                select(Experiment).where(Experiment.id == experiment_id)
            )
            experiment = result.scalar_one_or_none()
        elif asset_id:
            result = await db.execute(
                select(Experiment)
                .where(Experiment.asset_id == asset_id)
                .order_by(desc(Experiment.created_at))
                .limit(limit)
            )
            experiment = result.scalar_one_or_none()
        else:
            return {}

        if not experiment:
            return {}

        # Get variants
        variants_result = await db.execute(
            select(ExperimentVariant)
            .where(ExperimentVariant.experiment_id == experiment.id)
        )
        variants = variants_result.scalars().all()

        # Get assignment counts per variant
        variant_data = []
        for v in variants:
            count_result = await db.execute(
                select(func.count(ExperimentAssignment.id))
                .where(ExperimentAssignment.variant_id == v.id)
            )
            count = count_result.scalar() or 0
            variant_data.append({
                "variant_id": str(v.id),
                "name": v.variant_key,
                "traffic_allocation": float(v.traffic_percentage),
                "assignment_count": count,
                "is_control": v.is_control,
            })

        # Get most recent insight report
        insight_result = await db.execute(
            select(InsightReport)
            .where(InsightReport.experiment_id == experiment.id)
            .order_by(desc(InsightReport.generated_at))
            .limit(1)
        )
        insight = insight_result.scalar_one_or_none()

        return {
            "experiment_id": str(experiment.id),
            "name": experiment.experiment_name,
            "status": experiment.status,
            "hypothesis": "",
            "goal_metric": experiment.goal_metric,
            "total_assignments": sum(v["assignment_count"]
                                     for v in variant_data),
            "variants": variant_data,
            "recommended_winner": None,
            "insight_summary": insight.payload_json.get("summary")
            if insight and insight.payload_json else None,
        }

    except Exception as e:
        logger.error("experiment_index.get_experiment_context error: %s",
                      str(e))
        return {"error": str(e)}
