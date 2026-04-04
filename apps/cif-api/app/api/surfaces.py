from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.surface import SurfaceCreateIn, SurfaceOut, ResolvedSurface
from app.schemas.cast_payload import CastPayload, DecisionExplanationSummary
from app.services.surface_service import create_surface, resolve_surface
from app.models.surface import Surface, SurfaceVersion
from app.db.session import get_db
from app.core.auth import require_api_key
import uuid

router = APIRouter(prefix="/surfaces", tags=["surfaces"])


@router.get("", response_model=list[SurfaceOut])
async def list_surfaces(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    result = await db.execute(select(Surface).order_by(Surface.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=SurfaceOut, status_code=201)
async def create_surface_endpoint(
    data: SurfaceCreateIn,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    surface, errors = await create_surface(db, data)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return surface


@router.get("/{surface_id}/resolve", response_model=ResolvedSurface)
async def resolve_surface_endpoint(
    surface_id: uuid.UUID,
    request: Request,
    x_cycle_id: str = Header(..., alias="X-Cycle-ID"),
    x_cast_id: str = Header(..., alias="X-Cast-ID"),
    x_pla_band: str = Header(..., alias="X-PLA-Band"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    trace_id: str = getattr(request.state, "trace_id", str(uuid.uuid4()))
    cast_payload = CastPayload(
        cast_id=x_cast_id,
        cycle_id=x_cycle_id,
        trace_id=trace_id,
        pla_band=x_pla_band,
        decision_explanation_summary=DecisionExplanationSummary(
            primary_reason="CAST-routed execution",
            pla_band=x_pla_band,
            confidence_sufficient=True,
            review_required=False,
        ),
    )
    resolved = await resolve_surface(
        db,
        surface_id,
        cycle_id=x_cycle_id,
        trace_id=trace_id,
        cast_id=x_cast_id,
        cast_payload=cast_payload,
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Surface not found")
    return resolved


@router.get("/{surface_id}/versions/{version_id}")
async def get_version(
    surface_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    result = await db.execute(
        select(SurfaceVersion).where(
            SurfaceVersion.id == version_id,
            SurfaceVersion.surface_id == surface_id,
        )
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": str(v.id),
        "surface_id": str(v.surface_id),
        "version_number": v.version_number,
        "review_state": v.review_state,
        "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
        "published_at": v.published_at.isoformat() if v.published_at else None,
    }
