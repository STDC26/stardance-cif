from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.surface import SurfaceCreateIn, SurfaceOut, ResolvedSurface
from app.services.surface_service import create_surface, resolve_surface
from app.db.session import get_db
import uuid

router = APIRouter(prefix="/surfaces", tags=["surfaces"])


@router.post("", response_model=SurfaceOut, status_code=201)
async def create_surface_endpoint(
    data: SurfaceCreateIn,
    db: AsyncSession = Depends(get_db)
):
    surface, errors = await create_surface(db, data)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return surface


@router.get("/{surface_id}/resolve", response_model=ResolvedSurface)
async def resolve_surface_endpoint(
    surface_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    resolved = await resolve_surface(db, surface_id)
    if not resolved:
        raise HTTPException(status_code=404, detail="Surface not found")
    return resolved
