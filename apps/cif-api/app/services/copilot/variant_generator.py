"""
CIF Variant Generator — Phase-6 Sprint-5

Generates AI-assisted experiment variant suggestions.
Uses existing experiment context to propose new variants.
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

VARIANT_SYSTEM_PROMPT = """You are a creative intelligence assistant
that generates experiment variant suggestions. Given context about an
existing experiment and its variants, suggest new variants that could
improve performance.

Return ONLY valid JSON with these keys:
- variants: array of objects, each with:
  - variant_key: string (kebab-case identifier)
  - description: string (what this variant changes)
  - hypothesis: string (why this variant might perform better)
  - suggested_traffic_percentage: number (0-100)
- rationale: string (overall reasoning for these suggestions)

Do not include any text outside the JSON object."""


def _parse_json_response(text: str) -> dict:
    """Extracts JSON from LLM response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


async def generate_variants(
    db: AsyncSession,
    experiment_id: UUID,
    asset_id: Optional[UUID] = None,
    brief: Optional[str] = None,
) -> dict:
    """
    Generates AI-assisted variant suggestions for an experiment.

    Args:
        db:             AsyncSession
        experiment_id:  UUID of the experiment
        asset_id:       Optional asset UUID for additional context
        brief:          Optional freeform brief for variant direction

    Returns:
        dict with keys: draft, status, experiment_id, provider,
                        latency_ms, context_keys, error
    """
    try:
        context = await build_context(
            request=RetrievalRequest(
                experiment_id=experiment_id,
                asset_id=asset_id,
                include_signals=True,
                include_experiment=True,
            ),
            db=db,
        )

        if not context:
            return {"error": "No experiment context retrieved",
                    "experiment_id": str(experiment_id)}

        prompt = (
            f"Suggest new variants for this experiment.\n"
            f"Experiment: {context.get('experiment_name', 'Unknown')}\n"
            f"Status: {context.get('experiment_status', 'Unknown')}\n"
            f"Goal metric: "
            f"{context.get('experiment_goal_metric', 'Unknown')}\n"
            f"Total assignments: "
            f"{context.get('experiment_total_assignments', 0)}\n"
        )

        if brief:
            prompt += f"Direction: {brief}\n"

        # Add existing variant data
        for i in range(1, 4):
            name = context.get(f"variant_{i}_name")
            if name:
                prompt += (
                    f"Existing variant {i}: {name} — "
                    f"{context.get(f'variant_{i}_assignments', 0)} "
                    f"assignments, control="
                    f"{context.get(f'variant_{i}_is_control', False)}\n"
                )

        result = await generate(
            task_type=AITaskType.ASSET_DRAFT,
            prompt=prompt,
            context=context,
            system=VARIANT_SYSTEM_PROMPT,
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
            "experiment_id": str(experiment_id),
            "experiment_name": context.get("experiment_name", ""),
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("variant_generator error: %s", str(e))
        return {"error": str(e), "experiment_id": str(experiment_id)}
