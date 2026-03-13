"""
CIF AI Provider Package — Phase-6 Track 1

Public interface: import generate and AITaskType from this package.

Usage:
    from app.services.ai_provider import generate, AITaskType

    result = await generate(
        task_type=AITaskType.EXPERIMENT_SUMMARY,
        prompt="Summarize this experiment result...",
    )
    print(result["response"])
"""

from app.services.ai_provider.router import generate
from app.services.ai_provider.routing_policy import AITaskType

__all__ = ["generate", "AITaskType"]
