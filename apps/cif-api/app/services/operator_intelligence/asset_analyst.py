"""
CIF Asset Analyst — Phase-6 Sprint-4

Generates AI-assisted performance narratives for CIF assets.
Combines signal, experiment, and deployment context.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import build_context, RetrievalRequest
from app.services.ai_provider import generate, AITaskType

logger = logging.getLogger(__name__)

ASSET_SYSTEM_PROMPT = """You are an asset performance analyst for a
creative intelligence platform. Given asset performance data, provide:
1. A summary of asset performance
2. Key metrics and what they indicate
3. Whether experiments have improved performance
4. One recommendation for next optimization step
Be specific. Reference actual metrics from the context.
Keep response under 200 words."""


async def analyze_asset(
    db: AsyncSession,
    asset_id: Optional[UUID] = None,
    slug: Optional[str] = None,
) -> dict:
    """
    Generates an AI performance narrative for an asset.

    Returns:
        dict with keys: asset_name, asset_type, asset_status,
                        performance_summary, insight, provider,
                        latency_ms, context_keys
    """
    try:
        context = await build_context(
            request=RetrievalRequest(
                asset_id=asset_id,
                slug=slug,
                include_signals=True,
                include_experiment=True,
            ),
            db=db,
        )

        if not context:
            return {"error": "No asset context retrieved"}

        prompt = (
            f"Analyze the performance of this asset.\n"
            f"Asset: {context.get('asset_name', 'Unknown')}\n"
            f"Type: {context.get('asset_type', 'Unknown')}\n"
            f"Status: {context.get('asset_status', 'Unknown')}\n"
            f"Versions: {context.get('asset_version_count', 0)}\n"
            f"Latest version: "
            f"{context.get('asset_latest_version', 'None')}\n"
            f"Deployed version: "
            f"{context.get('asset_deployed_version', 'None')}\n"
            f"Total signal events: "
            f"{context.get('signal_total_events', 0)}\n"
            f"Experiment status: "
            f"{context.get('experiment_status', 'None')}\n"
            f"Recommended winner: "
            f"{context.get('experiment_recommended_winner', 'None')}\n"
        )

        result = await generate(
            task_type=AITaskType.OPERATOR_ASSISTANT,
            prompt=prompt,
            context=context,
            system=ASSET_SYSTEM_PROMPT,
        )

        return {
            "asset_name": context.get("asset_name", ""),
            "asset_type": context.get("asset_type", ""),
            "asset_status": context.get("asset_status", ""),
            "version_count": context.get("asset_version_count", 0),
            "deployed_version": context.get("asset_deployed_version", ""),
            "total_events": context.get("signal_total_events", 0),
            "asset_performance_summary": result["response"],
            "insight": result["response"],
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("asset_analyst error: %s", str(e))
        return {"error": str(e)}
