from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.deployment_service import get_active_deployment
from app.services.surface_service import resolve_surface
from app.models.deployment import DeploymentEnvironment

router = APIRouter(tags=["public"])


@router.get("/s/{slug}")
async def serve_surface(slug: str, response: Response, db: AsyncSession = Depends(get_db)):
    version, deployment = await get_active_deployment(db, slug, DeploymentEnvironment.production)
    if not version:
        raise HTTPException(status_code=404, detail="No active production deployment for this surface")
    resolved = await resolve_surface(db, version.surface_id)
    if not resolved:
        raise HTTPException(status_code=404, detail="Surface not found")
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Surrogate-Control"] = "max-age=3600"
    return {
        **resolved.model_dump(),
        "deployment_id": str(deployment.id),
        "environment": deployment.environment,
    }


@router.get("/s/{slug}/preview/{version_id}")
async def serve_preview(slug: str, version_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.surface import Surface, SurfaceVersion
    import uuid

    surface_result = await db.execute(select(Surface).where(Surface.slug == slug))
    surface = surface_result.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=404, detail="Surface not found")

    version_result = await db.execute(
        select(SurfaceVersion).where(
            SurfaceVersion.id == uuid.UUID(version_id),
            SurfaceVersion.surface_id == surface.id,
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    resolved = await resolve_surface(db, surface.id)
    return {**resolved.model_dump(), "environment": "preview"}


# ---------------------------------------------------------------------------
# Public QDS route — stable slug access, no auth required
# ---------------------------------------------------------------------------

from app.models.qds import QDSAsset, QDSFlow, QDSStep, QDSOutcome
from app.services.qds_deployment_service import get_active_qds_version


@router.get("/q/{slug}")
async def get_public_qds(slug: str, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Resolve a QDS by slug and return its active production deployment.
    No auth required — this is the public runtime entry point.
    """
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(QDSAsset).where(QDSAsset.slug == slug)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="QDS not found")

    version = await get_active_qds_version(asset.id, "production", db)
    if not version:
        raise HTTPException(
            status_code=404,
            detail="No active production deployment for this QDS"
        )

    result = await db.execute(
        sa_select(QDSFlow).where(QDSFlow.version_id == version.id)
    )
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="QDS flow not found")

    result = await db.execute(
        sa_select(QDSStep)
        .where(QDSStep.flow_id == flow.id)
        .order_by(QDSStep.position)
    )
    steps = result.scalars().all()

    result = await db.execute(
        sa_select(QDSOutcome).where(QDSOutcome.flow_id == flow.id)
    )
    outcomes = result.scalars().all()

    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Surrogate-Control"] = "max-age=3600"
    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "slug": asset.slug,
        "version_id": str(version.id),
        "version_number": version.version_number,
        "review_state": version.review_state,
        "flow": {
            "id": str(flow.id),
            "entry_step_id": str(flow.entry_step_id) if flow.entry_step_id else None,
            "steps": [
                {
                    "id": str(s.id),
                    "step_type": s.step_type if isinstance(s.step_type, str) else s.step_type.value,
                    "title": s.title,
                    "prompt": s.prompt,
                    "options": s.options,
                    "position": s.position,
                }
                for s in steps
            ],
            "outcomes": [
                {
                    "id": str(o.id),
                    "label": o.label,
                    "qualification_status": o.qualification_status if isinstance(o.qualification_status, str) else o.qualification_status.value,
                    "score_band_min": o.score_band_min,
                    "score_band_max": o.score_band_max,
                    "routing_target": o.routing_target,
                    "message": o.message,
                }
                for o in outcomes
            ],
        },
    }
