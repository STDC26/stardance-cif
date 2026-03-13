"""
CIF Context Builder — Phase-6 Sprint-3

Assembles normalized context bundles from raw retrieval data.
The context bundle is the structured input to the AI Router's
generate() call via the context parameter.

Usage:
    from app.services.retrieval import build_context, RetrievalRequest

    context = await build_context(
        request=RetrievalRequest(asset_id=uuid, include_signals=True),
        db=session,
    )
    result = await generate(
        task_type=AITaskType.EXPERIMENT_SUMMARY,
        prompt="Summarize this experiment.",
        context=context,
    )
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval.knowledge_router import route_retrieval

logger = logging.getLogger(__name__)


@dataclass
class RetrievalRequest:
    """Specifies what context to retrieve for an AI inference call."""
    asset_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    qds_asset_id: Optional[UUID] = None
    slug: Optional[str] = None
    include_signals: bool = True
    include_experiment: bool = True
    include_qds: bool = False


async def build_context(
    request: RetrievalRequest,
    db: AsyncSession,
) -> dict:
    """
    Assembles a normalized context bundle from platform data.

    The returned dict is passed directly to ai_provider.generate()
    as the context parameter, where it is injected into the prompt.

    Returns:
        Flat dict suitable for prompt injection. All values are
        strings or primitives — no nested objects.
    """
    raw = await route_retrieval(
        db=db,
        asset_id=request.asset_id,
        experiment_id=request.experiment_id,
        qds_asset_id=request.qds_asset_id,
        slug=request.slug,
        include_signals=request.include_signals,
        include_experiment=request.include_experiment,
        include_qds=request.include_qds,
    )

    bundle = {}

    # Asset section
    asset = raw.get("asset", {})
    if asset and not asset.get("error"):
        bundle["asset_name"] = asset.get("name", "")
        bundle["asset_type"] = asset.get("asset_type", "")
        bundle["asset_status"] = asset.get("status", "")
        bundle["asset_version_count"] = str(asset.get("version_count", 0))
        bundle["asset_latest_version"] = str(
            asset.get("latest_version", ""))
        bundle["asset_deployed_version"] = str(
            asset.get("deployed_version", ""))

    # Experiment section
    experiment = raw.get("experiment", {})
    if experiment and not experiment.get("error"):
        bundle["experiment_name"] = experiment.get("name", "")
        bundle["experiment_status"] = experiment.get("status", "")
        bundle["experiment_hypothesis"] = experiment.get(
            "hypothesis", "")
        bundle["experiment_goal_metric"] = experiment.get(
            "goal_metric", "")
        bundle["experiment_total_assignments"] = str(
            experiment.get("total_assignments", 0))
        bundle["experiment_recommended_winner"] = str(
            experiment.get("recommended_winner", ""))
        bundle["experiment_insight_summary"] = str(
            experiment.get("insight_summary", ""))

        variants = experiment.get("variants", [])
        for i, v in enumerate(variants[:3]):
            prefix = f"variant_{i+1}"
            bundle[f"{prefix}_name"] = v.get("name", "")
            bundle[f"{prefix}_assignments"] = str(
                v.get("assignment_count", 0))
            bundle[f"{prefix}_is_control"] = str(v.get("is_control", ""))

    # Signal section
    signals = raw.get("signals", {})
    if signals and not signals.get("error"):
        bundle["signal_total_events"] = str(
            signals.get("total_events", 0))
        bundle["signal_aggregate_count"] = str(
            signals.get("aggregate_count", 0))
        metrics = signals.get("metrics", [])
        for m in metrics[:5]:
            safe_key = m.get("metric_name", "").replace(".", "_")
            bundle[f"metric_{safe_key}"] = str(m.get("latest_value", ""))

    # QDS section
    qds = raw.get("qds", {})
    if qds and not qds.get("error"):
        bundle["qds_name"] = qds.get("name", "")
        bundle["qds_step_count"] = str(qds.get("step_count", 0))
        bundle["qds_completion_rate"] = str(
            qds.get("completion_rate", 0)) + "%"
        session_summary = qds.get("session_summary", {})
        bundle["qds_completed_sessions"] = str(
            session_summary.get("completed", 0))
        bundle["qds_total_sessions"] = str(
            sum(session_summary.values()) if session_summary else 0)

    logger.debug(
        "context_builder: bundle assembled with %d keys", len(bundle))
    return bundle
