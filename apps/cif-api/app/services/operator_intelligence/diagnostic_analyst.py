"""
CIF Diagnostic Analyst — Phase-6 Sprint-4

Analyzes QDS diagnostic flow performance.
Identifies drop-off points, step friction, and branching issues.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import build_context, RetrievalRequest
from app.services.ai_provider import generate, AITaskType
from app.services.ai_provider.routing_policy import AIProvider

logger = logging.getLogger(__name__)

DIAGNOSTIC_SYSTEM_PROMPT = """You are a diagnostic flow analyst for a
creative intelligence platform. Given QDS diagnostic data, identify:
1. Flow completion rate and what it indicates
2. Potential drop-off points based on step structure
3. Branching or complexity issues
4. One specific recommendation to improve completion
Be specific. Reference actual step counts and completion rates.
Keep response under 200 words."""


async def analyze_diagnostic(
    db: AsyncSession,
    qds_asset_id: Optional[UUID] = None,
    slug: Optional[str] = None,
) -> dict:
    """
    Generates an AI analysis of a QDS diagnostic flow.

    Returns:
        dict with keys: qds_name, step_count, completion_rate,
                        diagnostic_flow_analysis, insight,
                        provider, latency_ms, context_keys
    """
    try:
        context = await build_context(
            request=RetrievalRequest(
                qds_asset_id=qds_asset_id,
                slug=slug,
                include_signals=True,
                include_experiment=False,
                include_qds=True,
            ),
            db=db,
        )

        if not context:
            return {"error": "No QDS context retrieved"}

        prompt = (
            f"Analyze this diagnostic flow performance.\n"
            f"QDS name: {context.get('qds_name', 'Unknown')}\n"
            f"Step count: {context.get('qds_step_count', 0)}\n"
            f"Completion rate: "
            f"{context.get('qds_completion_rate', '0%')}\n"
            f"Completed sessions: "
            f"{context.get('qds_completed_sessions', 0)}\n"
            f"Total sessions: "
            f"{context.get('qds_total_sessions', 0)}\n"
            f"Total signal events: "
            f"{context.get('signal_total_events', 0)}\n"
        )

        total_sessions = context.get("qds_total_sessions", 0) or 0
        completed_count = context.get("qds_completed_sessions", 0) or 0
        drop_off_rate = (
            round((1 - completed_count / total_sessions) * 100, 1)
            if total_sessions else 0.0
        )
        variables = {
            "asset_name": context.get("qds_name", "Unknown"),
            "total_events": str(total_sessions),
            "event_breakdown": (
                f"total_sessions: {total_sessions}, "
                f"completed: {completed_count}, "
                f"drop_off_rate: {drop_off_rate}%"
            ),
            "time_period": "last 30 days",
        }

        # Route via SIGNAL_SUMMARY → cif.signal-insight prompt.
        # force_provider=REMOTE because SIGNAL_SUMMARY is a LOCAL task by
        # default but the diagnostic flow analysis must use the registered
        # remote template for drop-off narrative generation.
        result = await generate(
            task_type=AITaskType.SIGNAL_SUMMARY,
            prompt=prompt,
            context=context,
            system=DIAGNOSTIC_SYSTEM_PROMPT,
            force_provider=AIProvider.REMOTE,
            variables=variables,
        )

        return {
            "qds_name": context.get("qds_name", ""),
            "step_count": context.get("qds_step_count", 0),
            "completion_rate": context.get("qds_completion_rate", "0%"),
            "completed_sessions": context.get("qds_completed_sessions", 0),
            "total_sessions": context.get("qds_total_sessions", 0),
            "diagnostic_flow_analysis": result["response"],
            "insight": result["response"],
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("diagnostic_analyst error: %s", str(e))
        return {"error": str(e)}
