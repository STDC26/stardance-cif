from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import require_api_key
from app.models.surface import SurfaceVersion, ReviewState
from app.models.deployment import Deployment, DeploymentEnvironment
from app.services.deployment_service import (
    transition_version_state,
    deploy_surface,
    rollback_deployment,
)
from pydantic import BaseModel
import uuid

router = APIRouter(tags=["deployments"])


class StateTransitionIn(BaseModel):
    state: ReviewState


class DeployIn(BaseModel):
    environment: DeploymentEnvironment
    version_id: uuid.UUID


class RollbackIn(BaseModel):
    environment: DeploymentEnvironment


class DeploymentOut(BaseModel):
    id: uuid.UUID
    surface_id: uuid.UUID
    surface_version_id: uuid.UUID
    environment: DeploymentEnvironment
    status: str
    deployed_by: str | None
    deployed_at: str | None

    model_config = {"from_attributes": True}


class VersionOut(BaseModel):
    id: uuid.UUID
    surface_id: uuid.UUID
    version_number: int
    review_state: ReviewState
    reviewed_at: str | None
    published_at: str | None

    model_config = {"from_attributes": True}


@router.patch("/surfaces/{surface_id}/versions/{version_id}/state", response_model=VersionOut)
async def transition_state(
    surface_id: uuid.UUID,
    version_id: uuid.UUID,
    data: StateTransitionIn,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    version, error = await transition_version_state(db, surface_id, version_id, data.state, api_key)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return VersionOut(
        id=version.id,
        surface_id=version.surface_id,
        version_number=version.version_number,
        review_state=version.review_state,
        reviewed_at=version.reviewed_at.isoformat() if version.reviewed_at else None,
        published_at=version.published_at.isoformat() if version.published_at else None,
    )


@router.post("/surfaces/{surface_id}/deploy", response_model=DeploymentOut, status_code=201)
async def deploy(
    surface_id: uuid.UUID,
    data: DeployIn,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    deployment, error = await deploy_surface(db, surface_id, data.version_id, data.environment, api_key)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return DeploymentOut(
        id=deployment.id,
        surface_id=deployment.surface_id,
        surface_version_id=deployment.surface_version_id,
        environment=deployment.environment,
        status=deployment.status,
        deployed_by=deployment.deployed_by,
        deployed_at=deployment.deployed_at.isoformat() if deployment.deployed_at else None,
    )


@router.post("/surfaces/{surface_id}/rollback", response_model=DeploymentOut)
async def rollback(
    surface_id: uuid.UUID,
    data: RollbackIn,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    deployment, error = await rollback_deployment(db, surface_id, data.environment, api_key)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return DeploymentOut(
        id=deployment.id,
        surface_id=deployment.surface_id,
        surface_version_id=deployment.surface_version_id,
        environment=deployment.environment,
        status=deployment.status,
        deployed_by=deployment.deployed_by,
        deployed_at=deployment.deployed_at.isoformat() if deployment.deployed_at else None,
    )


@router.get("/surfaces/{surface_id}/deployments")
async def list_deployments(
    surface_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    result = await db.execute(
        select(Deployment)
        .where(Deployment.surface_id == surface_id)
        .order_by(Deployment.created_at.desc())
    )
    deployments = result.scalars().all()
    return [
        DeploymentOut(
            id=d.id,
            surface_id=d.surface_id,
            surface_version_id=d.surface_version_id,
            environment=d.environment,
            status=d.status,
            deployed_by=d.deployed_by,
            deployed_at=d.deployed_at.isoformat() if d.deployed_at else None,
        )
        for d in deployments
    ]
