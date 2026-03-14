"""
CIF Experiment Recommender — Phase-6 Sprint-5

Generates AI-assisted experiment recommendations for an asset.
Analyzes current performance context and suggests experiments
that could improve key metrics.
Returns structured JSON drafts with status="draft" enforced.
"""

import json
import logging
import re
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import build_context, RetrievalRequest
from app.services.ai_provider import generate, AITaskType

logger = logging.getLogger(__name__)

EXPERIMENT_REC_SYSTEM_PROMPT = """You are a creative intelligence assistant
that recommends experiments. Given context about an asset's performance,
suggest experiments that could improve key metrics.

Return ONLY valid JSON with these keys:
- experiments: array of objects, each with:
  - experiment_name: string (descriptive name)
  - hypothesis: string (what you expect to improve)
  - goal_metric: string (the metric to optimize)
  - variants: array of objects, each with:
    - variant_key: string (kebab-case)
    - description: string
    - is_control: boolean
  - priority: string (one of: high, medium, low)
- rationale: string (why these experiments matter now)

Do not include any text outside the JSON object."""


def _parse_json_response(text: str) -> dict:
    """Extracts JSON from LLM response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


async def recommend_experiments(
    db: AsyncSession,
    slug: Optional[str] = None,
    asset_id: Optional[UUID] = None,
    brief: Optional[str] = None,
) -> dict:
    """
    Generates AI-assisted experiment recommendations for an asset.

    Args:
        db:         AsyncSession
        slug:       Optional slug of the asset
        asset_id:   Optional asset UUID
        brief:      Optional freeform brief for experiment direction

    Returns:
        dict with keys: draft, status, asset_name, provider,
                        latency_ms, context_keys, error
    """
    try:
        context = {}
        if slug or asset_id:
            # Try surface lookup first
            context = await build_context(
                request=RetrievalRequest(
                    asset_id=asset_id,
                    slug=slug,
                    include_signals=True,
                    include_experiment=True,
                ),
                db=db,
            )

            # Fall back to QDS lookup if surface returned empty
            if not context and slug:
                context = await build_context(
                    request=RetrievalRequest(
                        slug=slug,
                        include_signals=True,
                        include_experiment=True,
                        include_qds=True,
                    ),
                    db=db,
                )

        if not context:
            return {"error": "No asset context retrieved"}

        asset_name = (context.get('asset_name') or
                      context.get('qds_name', 'Unknown'))

        prompt = (
            f"Recommend experiments for this asset.\n"
            f"Asset: {asset_name}\n"
            f"Type: {context.get('asset_type', 'Unknown')}\n"
            f"Status: {context.get('asset_status', 'Unknown')}\n"
            f"Total signal events: "
            f"{context.get('signal_total_events', 0)}\n"
        )

        if brief:
            prompt += f"Direction: {brief}\n"

        # Add existing experiment context if present
        if context.get('experiment_name'):
            prompt += (
                f"Current experiment: "
                f"{context.get('experiment_name', '')}\n"
                f"Experiment status: "
                f"{context.get('experiment_status', '')}\n"
                f"Goal metric: "
                f"{context.get('experiment_goal_metric', '')}\n"
            )

        # Add QDS context if present
        if context.get('qds_name'):
            prompt += (
                f"QDS name: {context.get('qds_name', '')}\n"
                f"QDS step count: {context.get('qds_step_count', 0)}\n"
                f"QDS completion rate: "
                f"{context.get('qds_completion_rate', '0%')}\n"
            )

        result = await generate(
            task_type=AITaskType.ASSET_DRAFT,
            prompt=prompt,
            context=context,
            system=EXPERIMENT_REC_SYSTEM_PROMPT,
        )

        try:
            draft = _parse_json_response(result["response"])
        except (json.JSONDecodeError, ValueError):
            draft = {"raw_response": result["response"]}

        # Governance: enforce draft status
        draft["status"] = "draft"

        return {
            "draft": draft,
            "status": "draft",
            "asset_name": asset_name,
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("experiment_recommender error: %s", str(e))
        return {"error": str(e)}
