"""
Analytics API — Phase-5
Exposes aggregated metrics from signal_aggregates and
experiment results from experiment_assignments.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from typing import Optional
from app.db.session import get_db
from app.core.auth import require_api_key
from app.models.experiment import (
    Experiment, ExperimentVariant, ExperimentAssignment, SignalAggregate
)
from app.models.qds import QDSAsset
from app.services.aggregation_jobs import run_all_jobs

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# ── helpers ──────────────────────────────────────────────────────────────

def _fmt_aggregate(row) -> dict:
    return {
        "aggregate_key": row.aggregate_key,
        "asset_id": str(row.asset_id) if row.asset_id else None,
        "asset_type": row.asset_type,
        "metric_name": row.metric_name,
        "metric_value": float(row.metric_value),
        "window_type": row.window_type,
        "window_start": row.window_start.isoformat() if row.window_start else None,
        "window_end": row.window_end.isoformat() if row.window_end else None,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        "experiment_id": str(row.experiment_id) if row.experiment_id else None,
        "variant_id": str(row.variant_id) if row.variant_id else None,
    }


# ── asset-level analytics ─────────────────────────────────────────────────

@router.get("/assets")
async def get_all_asset_analytics(
    asset_type: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    window_type: Optional[str] = Query("daily"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Returns aggregated metrics for all assets."""
    conditions = [
        SignalAggregate.experiment_id == None,
    ]
    if asset_type:
        conditions.append(SignalAggregate.asset_type == asset_type)
    if metric_name:
        conditions.append(SignalAggregate.metric_name == metric_name)
    if window_type:
        conditions.append(SignalAggregate.window_type == window_type)

    result = await db.execute(
        select(SignalAggregate)
        .where(and_(*conditions))
        .order_by(SignalAggregate.computed_at.desc())
    )
    rows = result.scalars().all()
    return [_fmt_aggregate(r) for r in rows]


@router.get("/assets/{asset_id}")
async def get_asset_analytics(
    asset_id: str,
    metric_name: Optional[str] = Query(None),
    window_type: Optional[str] = Query("daily"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Returns aggregated metrics for a specific asset."""
    import uuid as _uuid
    try:
        aid = _uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid asset_id")

    conditions = [
        SignalAggregate.asset_id == aid,
        SignalAggregate.experiment_id == None,
    ]
    if metric_name:
        conditions.append(SignalAggregate.metric_name == metric_name)
    if window_type:
        conditions.append(SignalAggregate.window_type == window_type)

    result = await db.execute(
        select(SignalAggregate)
        .where(and_(*conditions))
        .order_by(SignalAggregate.computed_at.desc())
    )
    rows = result.scalars().all()
    if not rows:
        return {"asset_id": asset_id, "metrics": [], "message": "No aggregates found. Run aggregation job first."}

    return {
        "asset_id": asset_id,
        "metrics": [_fmt_aggregate(r) for r in rows],
    }


@router.get("/qds")
async def get_qds_analytics(
    metric_name: Optional[str] = Query(None),
    window_type: Optional[str] = Query("daily"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Returns aggregated metrics for all QDS assets."""
    conditions = [
        SignalAggregate.asset_type == "qds",
        SignalAggregate.experiment_id == None,
    ]
    if metric_name:
        conditions.append(SignalAggregate.metric_name == metric_name)
    if window_type:
        conditions.append(SignalAggregate.window_type == window_type)

    result = await db.execute(
        select(SignalAggregate)
        .where(and_(*conditions))
        .order_by(SignalAggregate.computed_at.desc())
    )
    rows = result.scalars().all()
    return [_fmt_aggregate(r) for r in rows]


@router.get("/surfaces")
async def get_surface_analytics(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """TCE-12 — live CQX analytics for every surface with at least one signal.

    Queries ``signal_events`` directly; no dependency on the aggregation job.
    Returns per-surface view/conversion/impression counts, CQX-stage
    breakdown for component_impressions, and stage-to-stage drop-off.
    """
    rows = (await db.execute(text("""
        SELECT
            s.id                            AS surface_id,
            s.slug                          AS slug,
            s.name                          AS name,
            COUNT(*) FILTER (WHERE se.event_type = 'surface_view')        AS total_views,
            COUNT(*) FILTER (WHERE se.event_type = 'conversion')          AS total_conversions,
            COUNT(*) FILTER (WHERE se.event_type = 'component_impression') AS total_impressions,
            COUNT(se.id)                                                  AS total_signals,
            MAX(se.created_at)              AS last_signal_at
        FROM surfaces s
        JOIN signal_events se ON se.surface_id = s.id
        GROUP BY s.id, s.slug, s.name
        ORDER BY last_signal_at DESC
    """))).mappings().all()

    out: list[dict] = []
    for r in rows:
        surface_id = r["surface_id"]

        # CQX stage breakdown from component_impression event_data.
        stage_rows = (await db.execute(text("""
            SELECT
                event_data->>'cqx_stage' AS cqx_stage,
                COUNT(*)                 AS cnt
            FROM signal_events
            WHERE surface_id = :sid
              AND event_type = 'component_impression'
              AND event_data ? 'cqx_stage'
              AND event_data->>'cqx_stage' IS NOT NULL
            GROUP BY event_data->>'cqx_stage'
        """), {"sid": surface_id})).mappings().all()
        breakdown = {row["cqx_stage"]: int(row["cnt"]) for row in stage_rows}

        # Stage-to-stage drop-off (percentage of the earlier stage lost).
        def _drop(a: str, b: str) -> Optional[str]:
            av, bv = breakdown.get(a, 0), breakdown.get(b, 0)
            if av <= 0:
                return None
            pct = (av - bv) / av * 100
            return f"{max(pct, 0):.1f}%"

        drop_off = {
            "context_to_outcome":      _drop("context", "outcome"),
            "outcome_to_conviction":   _drop("outcome", "conviction"),
            "conviction_to_direction": _drop("conviction", "direction"),
            "direction_to_action":     _drop("direction", "action"),
        }

        views = int(r["total_views"] or 0)
        convs = int(r["total_conversions"] or 0)
        conv_rate = f"{(convs / views * 100):.1f}%" if views > 0 else "0.0%"

        out.append({
            "surface_id":          str(surface_id),
            "slug":                r["slug"],
            "surface_name":        r["name"],
            "total_views":         views,
            "total_conversions":   convs,
            "conversion_rate":     conv_rate,
            "total_impressions":   int(r["total_impressions"] or 0),
            "total_signals":       int(r["total_signals"] or 0),
            "cqx_stage_breakdown": breakdown,
            "cqx_drop_off":        drop_off,
            "last_signal_at": (
                r["last_signal_at"].isoformat()
                if r["last_signal_at"] else None
            ),
        })

    return out


@router.get("/qds/{slug}")
async def get_qds_live_analytics(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """TCE-12 — live per-QDS session analytics + per-step drop-off."""
    # Resolve slug → QDS asset
    asset_row = (await db.execute(text(
        "SELECT id, name FROM qds_assets WHERE slug = :slug"
    ), {"slug": slug})).mappings().first()
    if asset_row is None:
        raise HTTPException(status_code=404, detail=f"QDS not found: {slug}")
    asset_id = asset_row["id"]

    session_totals = (await db.execute(text("""
        SELECT
            COUNT(*)                                                  AS total,
            COUNT(*) FILTER (WHERE status = 'completed')              AS completed,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
              FILTER (WHERE status = 'completed' AND completed_at IS NOT NULL)
                AS avg_completion_seconds
        FROM qds_sessions
        WHERE asset_id = :aid
    """), {"aid": asset_id})).mappings().first()

    total_sessions = int(session_totals["total"] or 0) if session_totals else 0
    completed = int(session_totals["completed"] or 0) if session_totals else 0
    avg_seconds = (
        float(session_totals["avg_completion_seconds"])
        if session_totals and session_totals["avg_completion_seconds"] is not None
        else None
    )
    completion_rate = (
        f"{(completed / total_sessions * 100):.1f}%"
        if total_sessions > 0 else "0.0%"
    )

    # Per-step drop-off from answer_submitted signals.
    step_rows = (await db.execute(text("""
        SELECT
            event_data->>'step_position' AS step_position,
            COUNT(*)                     AS cnt
        FROM signal_events
        WHERE surface_id = :aid
          AND event_type = 'answer_submitted'
          AND event_data ? 'step_position'
          AND event_data->>'step_position' IS NOT NULL
        GROUP BY event_data->>'step_position'
        ORDER BY step_position
    """), {"aid": asset_id})).mappings().all()
    step_drop_off = {row["step_position"]: int(row["cnt"]) for row in step_rows}

    return {
        "slug":                           slug,
        "asset_id":                       str(asset_id),
        "qds_name":                       asset_row["name"],
        "total_sessions":                 total_sessions,
        "completed_sessions":             completed,
        "completion_rate":                completion_rate,
        "avg_completion_time_seconds":    (
            round(avg_seconds, 2) if avg_seconds is not None else None
        ),
        "step_drop_off":                  step_drop_off,
    }


@router.post("/aggregate")
async def trigger_live_aggregate(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """TCE-12 — manual-trigger counters over live signal_events data.

    Returns how many surfaces have at least one signal and how many rows
    currently sit in signal_events. No cache is written — this endpoint
    exists as a trigger-shaped health check for future Railway cron.
    """
    import time as _time
    start = _time.monotonic()

    surfaces_row = (await db.execute(text("""
        SELECT COUNT(DISTINCT s.id) AS cnt
        FROM surfaces s
        JOIN signal_events se ON se.surface_id = s.id
    """))).mappings().first()
    signals_row = (await db.execute(text(
        "SELECT COUNT(*) AS cnt FROM signal_events"
    ))).mappings().first()

    return {
        "surfaces_processed": int(surfaces_row["cnt"] or 0) if surfaces_row else 0,
        "signals_processed":  int(signals_row["cnt"] or 0) if signals_row else 0,
        "latency_ms":         int((_time.monotonic() - start) * 1000),
    }


# ── experiment analytics ──────────────────────────────────────────────────

@router.get("/experiments")
async def get_all_experiment_analytics(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Returns all experiments with variant session counts."""
    result = await db.execute(
        select(Experiment).order_by(Experiment.created_at.desc())
    )
    experiments = result.scalars().all()

    output = []
    for exp in experiments:
        variants_result = await db.execute(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == exp.id
            )
        )
        variants = variants_result.scalars().all()

        variant_data = []
        total_sessions = 0
        for v in variants:
            count_result = await db.execute(
                select(ExperimentAssignment).where(
                    ExperimentAssignment.variant_id == v.id
                )
            )
            session_count = len(count_result.scalars().all())
            total_sessions += session_count
            variant_data.append({
                "variant_key": v.variant_key,
                "variant_id": str(v.id),
                "is_control": v.is_control,
                "traffic_percentage": float(v.traffic_percentage),
                "sessions": session_count,
                "qds_version_id": str(v.qds_version_id) if v.qds_version_id else None,
                "surface_version_id": str(v.surface_version_id) if v.surface_version_id else None,
            })

        output.append({
            "experiment_id": exp.experiment_id,
            "experiment_name": exp.experiment_name,
            "asset_id": str(exp.asset_id),
            "asset_type": exp.asset_type,
            "status": exp.status,
            "goal_metric": exp.goal_metric,
            "total_sessions": total_sessions,
            "variants": variant_data,
        })

    return output


@router.get("/experiments/{experiment_id}")
async def get_experiment_analytics(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """
    Returns detailed analytics for one experiment.
    Includes per-variant session counts, traffic share,
    and goal metric values from signal_aggregates if available.
    """
    exp_result = await db.execute(
        select(Experiment).where(
            Experiment.experiment_id == experiment_id
        )
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    variants_result = await db.execute(
        select(ExperimentVariant).where(
            ExperimentVariant.experiment_id == exp.id
        )
    )
    variants = variants_result.scalars().all()

    variant_results = []
    total_sessions = 0

    for v in variants:
        assign_result = await db.execute(
            select(ExperimentAssignment).where(
                ExperimentAssignment.variant_id == v.id
            )
        )
        sessions = len(assign_result.scalars().all())
        total_sessions += sessions

        # Pull goal metric from signal_aggregates if available
        goal_value = None
        if exp.goal_metric:
            agg_result = await db.execute(
                select(SignalAggregate).where(
                    and_(
                        SignalAggregate.experiment_id == exp.id,
                        SignalAggregate.variant_id == v.id,
                        SignalAggregate.metric_name == exp.goal_metric,
                    )
                ).order_by(SignalAggregate.computed_at.desc()).limit(1)
            )
            agg = agg_result.scalar_one_or_none()
            if agg:
                goal_value = float(agg.metric_value)

        variant_results.append({
            "variant_id": str(v.id),
            "variant_key": v.variant_key,
            "is_control": v.is_control,
            "traffic_percentage": float(v.traffic_percentage),
            "sessions": sessions,
            "goal_metric": exp.goal_metric,
            "goal_metric_value": goal_value,
            "qds_version_id": str(v.qds_version_id) if v.qds_version_id else None,
            "surface_version_id": str(v.surface_version_id) if v.surface_version_id else None,
        })

    # Compute traffic share
    for r in variant_results:
        r["traffic_share"] = round(
            r["sessions"] / total_sessions * 100, 2
        ) if total_sessions > 0 else 0.0

    # Recommend winner by sessions (goal metric value when available)
    recommended_winner = None
    if variant_results:
        by_goal = [r for r in variant_results if r["goal_metric_value"] is not None]
        if by_goal:
            recommended_winner = max(
                by_goal, key=lambda r: r["goal_metric_value"]
            )["variant_key"]
        else:
            recommended_winner = max(
                variant_results, key=lambda r: r["sessions"]
            )["variant_key"]

    return {
        "experiment_id": exp.experiment_id,
        "experiment_name": exp.experiment_name,
        "asset_id": str(exp.asset_id),
        "asset_type": exp.asset_type,
        "status": exp.status,
        "goal_metric": exp.goal_metric,
        "total_sessions": total_sessions,
        "variant_results": variant_results,
        "recommended_winner": recommended_winner,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }


# ── aggregation trigger ───────────────────────────────────────────────────

@router.post("/run-aggregation")
async def trigger_analytics_aggregation(
    window_type: str = Query("daily"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """
    Manually trigger all aggregation jobs.
    Authenticated endpoint for operator use.
    Returns job summary.
    """
    result = await run_all_jobs(db, window_type=window_type)
    return result
