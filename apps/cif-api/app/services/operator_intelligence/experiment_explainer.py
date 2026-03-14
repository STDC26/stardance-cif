"""
CIF Experiment Explainer — Phase-6 Sprint-4

Generates AI-assisted explanations of experiment results
and variant performance using retrieval context.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import build_context, RetrievalRequest
from app.services.ai_provider import generate, AITaskType

logger = logging.getLogger(__name__)

EXPERIMENT_SYSTEM_PROMPT = """You are a concise experiment analyst for a
creative intelligence platform. Given experiment data, explain:
1. Which variant performed better and why
2. What the key metrics indicate
3. One clear optimization recommendation
Be specific. Reference actual metrics from the context.
Keep response under 200 words."""


async def explain_experiment(
    db: AsyncSession,
    experiment_id: UUID,
    asset_id: UUID = None,
) -> dict:
    """
    Generates an AI explanation of experiment results.

    Returns:
        dict with keys: experiment_summary, variant_comparison,
                        recommended_winner, insight, latency_ms,
                        provider, context_keys
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
            return {"error": "No context retrieved for experiment",
                    "experiment_id": str(experiment_id)}

        prompt = (
            f"Explain the results of this experiment.\n"
            f"Experiment: {context.get('experiment_name', 'Unknown')}\n"
            f"Status: {context.get('experiment_status', 'Unknown')}\n"
            f"Goal metric: {context.get('experiment_goal_metric', 'Unknown')}\n"
            f"Total assignments: "
            f"{context.get('experiment_total_assignments', 0)}\n"
            f"Recommended winner: "
            f"{context.get('experiment_recommended_winner', 'None')}\n"
            f"Hypothesis: {context.get('experiment_hypothesis', 'None')}\n"
        )

        # Add variant data
        for i in range(1, 4):
            name = context.get(f"variant_{i}_name")
            if name:
                prompt += (
                    f"Variant {i}: {name} — "
                    f"{context.get(f'variant_{i}_assignments', 0)} "
                    f"assignments, control="
                    f"{context.get(f'variant_{i}_is_control', False)}\n"
                )

        result = await generate(
            task_type=AITaskType.EXPERIMENT_SUMMARY,
            prompt=prompt,
            context=context,
            system=EXPERIMENT_SYSTEM_PROMPT,
        )

        return {
            "experiment_id": str(experiment_id),
            "experiment_name": context.get("experiment_name", ""),
            "experiment_status": context.get("experiment_status", ""),
            "recommended_winner": context.get(
                "experiment_recommended_winner", ""),
            "total_assignments": context.get(
                "experiment_total_assignments", 0),
            "experiment_summary": result["response"],
            "variant_comparison": {
                f"variant_{i}": {
                    "name": context.get(f"variant_{i}_name", ""),
                    "assignments": context.get(
                        f"variant_{i}_assignments", 0),
                }
                for i in range(1, 4)
                if context.get(f"variant_{i}_name")
            },
            "insight": result["response"],
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("experiment_explainer error: %s", str(e))
        return {"error": str(e), "experiment_id": str(experiment_id)}
