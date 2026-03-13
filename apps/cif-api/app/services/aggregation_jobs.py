"""
Aggregation Jobs — Phase-5

Computes signal aggregates from raw signal_events and writes
results to signal_aggregates table. Designed to be called
periodically (cron) or manually via internal API.

Aggregation is idempotent — re-running overwrites existing
aggregate rows for the same aggregate_key.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, text, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.experiment import SignalAggregate


async def compute_asset_aggregates(
    db: AsyncSession,
    asset_id: Optional[str] = None,
    window_hours: int = 24,
    window_type_override: Optional[str] = None,
) -> list[SignalAggregate]:
    """
    Compute per-asset signal aggregates for a rolling window.
    If asset_id is None, computes for all assets with recent signals.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    # Build the query for signal counts by asset and event_type
    query = text("""
        SELECT
            surface_id AS asset_id,
            event_type,
            COALESCE(event_data->>'asset_type', 'conversion_surface') AS asset_type,
            COUNT(*) AS event_count
        FROM signal_events
        WHERE created_at >= :window_start
          AND created_at <= :window_end
          AND surface_id IS NOT NULL
        GROUP BY surface_id, event_type,
                 COALESCE(event_data->>'asset_type', 'conversion_surface')
    """)

    params = {"window_start": window_start, "window_end": now}
    if asset_id:
        query = text("""
            SELECT
                surface_id AS asset_id,
                event_type,
                COALESCE(event_data->>'asset_type', 'conversion_surface') AS asset_type,
                COUNT(*) AS event_count
            FROM signal_events
            WHERE created_at >= :window_start
              AND created_at <= :window_end
              AND surface_id = :asset_id
            GROUP BY surface_id, event_type,
                     COALESCE(event_data->>'asset_type', 'conversion_surface')
        """)
        params["asset_id"] = uuid.UUID(asset_id)

    result = await db.execute(query, params)
    rows = result.fetchall()

    aggregates = []
    for row in rows:
        wt = window_type_override or f"rolling_{window_hours}h"
        agg_key = f"{row.asset_id}:{row.event_type}:{wt}"

        # Upsert: delete existing, then insert
        await db.execute(
            delete(SignalAggregate).where(
                SignalAggregate.aggregate_key == agg_key
            )
        )

        agg = SignalAggregate(
            aggregate_key=agg_key,
            asset_id=row.asset_id,
            asset_type=row.asset_type,
            metric_name=row.event_type,
            metric_value=row.event_count,
            window_type=window_type_override or f"rolling_{window_hours}h",
            window_start=window_start,
            window_end=now,
        )
        db.add(agg)
        aggregates.append(agg)

    await db.commit()
    return aggregates


async def compute_experiment_aggregates(
    db: AsyncSession,
    experiment_id: Optional[str] = None,
    window_hours: int = 24,
) -> list[SignalAggregate]:
    """
    Compute per-experiment, per-variant signal aggregates.
    Joins experiment_assignments to signal_events via session_id
    to attribute signals to variants.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    query = text("""
        SELECT
            ea.experiment_id,
            ea.variant_id,
            se.event_type,
            COALESCE(se.event_data->>'asset_type', 'conversion_surface') AS asset_type,
            COUNT(*) AS event_count
        FROM signal_events se
        JOIN experiment_assignments ea ON ea.session_id = se.session_id
        WHERE se.created_at >= :window_start
          AND se.created_at <= :window_end
        GROUP BY ea.experiment_id, ea.variant_id, se.event_type,
                 COALESCE(se.event_data->>'asset_type', 'conversion_surface')
    """)

    params = {"window_start": window_start, "window_end": now}
    result = await db.execute(query, params)
    rows = result.fetchall()

    aggregates = []
    for row in rows:
        agg_key = f"exp:{row.experiment_id}:{row.variant_id}:{row.event_type}:{window_hours}h"

        await db.execute(
            delete(SignalAggregate).where(
                SignalAggregate.aggregate_key == agg_key
            )
        )

        agg = SignalAggregate(
            aggregate_key=agg_key,
            experiment_id=row.experiment_id,
            variant_id=row.variant_id,
            asset_type=row.asset_type,
            metric_name=row.event_type,
            metric_value=row.event_count,
            window_type=f"rolling_{window_hours}h",
            window_start=window_start,
            window_end=now,
        )
        db.add(agg)
        aggregates.append(agg)

    await db.commit()
    return aggregates


async def run_all_aggregations(
    db: AsyncSession,
    window_hours: int = 24,
) -> dict:
    """Run both asset and experiment aggregations. Returns summary."""
    asset_aggs = await compute_asset_aggregates(db, window_hours=window_hours)
    exp_aggs = await compute_experiment_aggregates(db, window_hours=window_hours)
    return {
        "status": "complete",
        "asset_aggregates": len(asset_aggs),
        "experiment_aggregates": len(exp_aggs),
        "window_hours": window_hours,
    }


# ---------------------------------------------------------------------------
# Track 3 — additional jobs and helpers
# ---------------------------------------------------------------------------

def _build_aggregate_key(
    asset_id: str,
    surface_version_id: Optional[str],
    experiment_id: Optional[str],
    variant_id: Optional[str],
    metric_name: str,
    window_type: str,
    window_start: datetime,
    window_end: datetime,
) -> str:
    parts = [asset_id or "none"]
    if experiment_id:
        parts.append(f"exp:{experiment_id}")
    if variant_id:
        parts.append(f"var:{variant_id}")
    if surface_version_id:
        parts.append(f"sv:{surface_version_id}")
    parts.append(metric_name)
    parts.append(window_type)
    parts.append(window_start.strftime("%Y%m%d"))
    parts.append(window_end.strftime("%Y%m%d"))
    return ":".join(parts)


async def run_asset_performance_job(
    db: AsyncSession,
    window_type: str = "daily",
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
) -> dict:
    """
    Job 1 — Asset Performance Aggregation.
    Wraps compute_asset_aggregates with window_type interface.
    """
    if window_end is None:
        window_end = datetime.now(timezone.utc)
    if window_start is None:
        window_start = window_end - timedelta(hours=24)

    # Compute hours from the window
    delta = window_end - window_start
    window_hours = max(int(delta.total_seconds() / 3600), 1)

    aggs = await compute_asset_aggregates(db, window_hours=window_hours, window_type_override=window_type)
    return {
        "job": "asset_performance",
        "window_type": window_type,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "rows_written": len(aggs),
    }


async def run_experiment_variant_job(
    db: AsyncSession,
    window_type: str = "daily",
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
) -> dict:
    """
    Job 2 — Experiment Variant Aggregation.
    Computes sessions-per-variant from experiment_assignments.
    Upserts into signal_aggregates grouped by experiment + variant.
    """
    if window_end is None:
        window_end = datetime.now(timezone.utc)
    if window_start is None:
        window_start = window_end - timedelta(hours=24)

    rows_written = 0

    assign_query = text("""
        SELECT
            ea.experiment_id,
            ea.variant_id,
            COUNT(DISTINCT ea.session_id) AS session_count,
            e.asset_id,
            e.asset_type
        FROM experiment_assignments ea
        JOIN experiments e ON e.id = ea.experiment_id
        WHERE ea.assigned_at BETWEEN :start AND :end
        GROUP BY ea.experiment_id, ea.variant_id, e.asset_id, e.asset_type
    """)

    result = await db.execute(
        assign_query,
        {"start": window_start, "end": window_end}
    )
    rows = result.fetchall()

    for row in rows:
        agg_key = _build_aggregate_key(
            str(row.asset_id),
            None,
            str(row.experiment_id),
            str(row.variant_id),
            "sessions",
            window_type,
            window_start,
            window_end,
        )

        # Upsert: delete then insert
        await db.execute(
            delete(SignalAggregate).where(
                SignalAggregate.aggregate_key == agg_key
            )
        )

        agg = SignalAggregate(
            aggregate_key=agg_key,
            asset_id=row.asset_id,
            experiment_id=row.experiment_id,
            variant_id=row.variant_id,
            asset_type=row.asset_type,
            metric_name="sessions",
            metric_value=float(row.session_count),
            window_type=window_type,
            window_start=window_start,
            window_end=window_end,
        )
        db.add(agg)
        rows_written += 1

    await db.commit()

    return {
        "job": "experiment_variant",
        "window_type": window_type,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "rows_written": rows_written,
    }


async def run_all_jobs(
    db: AsyncSession,
    window_type: str = "daily",
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
) -> dict:
    results = []
    r1 = await run_asset_performance_job(db, window_type, window_start, window_end)
    results.append(r1)
    r2 = await run_experiment_variant_job(db, window_type, window_start, window_end)
    results.append(r2)
    return {
        "status": "complete",
        "jobs_run": len(results),
        "results": results,
    }
