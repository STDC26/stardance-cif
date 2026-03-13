"""
Internal API — Phase-5

Endpoints for internal operations: aggregation jobs, health checks,
and admin tooling. No API key required — these are meant to be called
by internal cron jobs, admin scripts, or the operator console.

Mount at /internal (no /api/v1 prefix).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.aggregation_jobs import run_all_aggregations

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/run-aggregation-job")
async def trigger_aggregation_job(
    window_hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger signal aggregation. Called by cron or admin."""
    result = await run_all_aggregations(db, window_hours=window_hours)
    return result
