"""
CIF Signal Index — Phase-6 Sprint-3

Retrieves signal aggregates and event trends for an asset.
Queries: signal_aggregates, signal_events tables.
READ-ONLY.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import SignalAggregate
from app.models.signal import SignalEvent

logger = logging.getLogger(__name__)


async def get_signal_context(
    db: AsyncSession,
    asset_id: UUID,
    limit_aggregates: int = 10,
    limit_events: int = 5,
) -> dict:
    """
    Returns signal aggregate metrics and recent event type distribution
    for a given asset.
    """
    try:
        # Get signal aggregates for this asset
        agg_result = await db.execute(
            select(SignalAggregate)
            .where(SignalAggregate.asset_id == asset_id)
            .order_by(desc(SignalAggregate.window_start))
            .limit(limit_aggregates)
        )
        aggregates = agg_result.scalars().all()

        # Get event type distribution (SignalEvent uses surface_id)
        event_dist_result = await db.execute(
            select(
                SignalEvent.event_type,
                func.count(SignalEvent.id).label("count"),
            )
            .where(SignalEvent.surface_id == asset_id)
            .group_by(SignalEvent.event_type)
            .order_by(desc("count"))
            .limit(limit_events)
        )
        event_distribution = [
            {"event_type": row.event_type.value
             if hasattr(row.event_type, "value") else str(row.event_type),
             "count": row.count}
            for row in event_dist_result
        ]

        # Summarize aggregate metrics
        metric_summary = {}
        for agg in aggregates:
            key = agg.metric_name
            if key not in metric_summary:
                metric_summary[key] = {
                    "metric_name": key,
                    "latest_value": float(agg.metric_value),
                    "sample_count": 1,
                }

        return {
            "asset_id": str(asset_id),
            "aggregate_count": len(aggregates),
            "metrics": list(metric_summary.values()),
            "event_distribution": event_distribution,
            "total_events": sum(e["count"] for e in event_distribution),
        }

    except Exception as e:
        logger.error("signal_index.get_signal_context error: %s", str(e))
        return {"error": str(e)}
