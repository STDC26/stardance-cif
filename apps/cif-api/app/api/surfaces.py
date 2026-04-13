from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.surface import SurfaceCreateIn, SurfaceOut, SurfaceSequenceIn, ResolvedSurface
from app.schemas.cast_payload import CastPayload, DecisionExplanationSummary
from app.services.surface_service import create_surface, resolve_surface
from app.services.cqx_sequencing_engine import sequence_surface
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
    surface, result = await create_surface(db, data)
    if surface is None:
        raise HTTPException(status_code=422, detail=result)

    cqx_sequencing = None
    if data.hcts_target_profile or data.scss_position:
        components = [
            c.model_dump()
            for section in (data.sections or [])
            for c in section.components
        ]
        seq = sequence_surface(
            hcts_profile=data.hcts_target_profile or {},
            scss_position=data.scss_position or "entry",
            cqx_intensity=data.cqx_intensity or "medium",
            components=components,
        )
        cqx_sequencing = {
            "conviction_expectation": seq.conviction_expectation,
            "stage_coverage": seq.stage_coverage,
            "validation": seq.validation,
            "failure_reason": seq.failure_reason,
        }

    return SurfaceOut(
        id=surface.id,
        current_version_id=result.id,
        name=surface.name,
        slug=surface.slug,
        description=surface.description,
        type=surface.type,
        status=surface.status,
        created_at=surface.created_at,
        cqx_sequencing=cqx_sequencing,
    )


@router.post("/sequence")
async def sequence_surface_endpoint(
    data: SurfaceSequenceIn,
    api_key: str = Depends(require_api_key),
):
    components = [c.model_dump() for c in data.components]
    result = sequence_surface(
        hcts_profile=data.hcts_target_profile or {},
        scss_position=data.scss_position,
        cqx_intensity=data.cqx_intensity,
        components=components,
    )
    return result.to_dict()


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
