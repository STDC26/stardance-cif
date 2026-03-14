"""
CIF Signal Interpreter — Phase-6 Sprint-4

Interprets behavioral signal trends for an asset.
Identifies patterns, anomalies, and drop-off indicators.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import build_context, RetrievalRequest
from app.services.ai_provider import generate, AITaskType

logger = logging.getLogger(__name__)

SIGNAL_SYSTEM_PROMPT = """You are a behavioral signal analyst for a
creative intelligence platform. Given signal data, identify:
1. Key trends in the signal metrics
2. Any concerning patterns or drop-off points
3. One actionable recommendation for improvement
Be specific. Reference actual metrics from the context.
Keep response under 200 words."""


async def interpret_signals(
    db: AsyncSession,
    asset_id: UUID,
) -> dict:
    """
    Generates an AI interpretation of signal trends for an asset.

    Returns:
        dict with keys: asset_id, signal_summary, total_events,
                        metrics, insight, provider, latency_ms
    """
    try:
        context = await build_context(
            request=RetrievalRequest(
                asset_id=asset_id,
                include_signals=True,
                include_experiment=False,
            ),
            db=db,
        )

        if not context:
            return {"error": "No signal context retrieved",
                    "asset_id": str(asset_id)}

        prompt = (
            f"Interpret the signal trends for this asset.\n"
            f"Asset: {context.get('asset_name', 'Unknown')}\n"
            f"Asset type: {context.get('asset_type', 'Unknown')}\n"
            f"Total events: {context.get('signal_total_events', 0)}\n"
            f"Aggregate count: "
            f"{context.get('signal_aggregate_count', 0)}\n"
        )

        # Add metric data
        for k, v in context.items():
            if k.startswith("metric_"):
                metric_name = k.replace("metric_", "").replace("_", ".")
                prompt += f"Metric {metric_name}: {v}\n"

        result = await generate(
            task_type=AITaskType.SIGNAL_SUMMARY,
            prompt=prompt,
            context=context,
            system=SIGNAL_SYSTEM_PROMPT,
        )

        return {
            "asset_id": str(asset_id),
            "asset_name": context.get("asset_name", ""),
            "total_events": context.get("signal_total_events", 0),
            "aggregate_count": context.get("signal_aggregate_count", 0),
            "signal_summary": result["response"],
            "insight": result["response"],
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("signal_interpreter error: %s", str(e))
        return {"error": str(e), "asset_id": str(asset_id)}
