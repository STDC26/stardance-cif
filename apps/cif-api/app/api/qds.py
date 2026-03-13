import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import require_api_key
from app.models.qds import QDSAsset, QDSVersion
from app.schemas.qds import QDSCreateIn, QDSVersionOut
from app.services.qds_service import create_qds_asset, resolve_qds

router = APIRouter(
    prefix="/qds",
    tags=["qds"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", status_code=201)
async def create_qds(data: QDSCreateIn, db: AsyncSession = Depends(get_db)):
    return await create_qds_asset(data, db)


@router.get("")
async def list_qds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QDSAsset).order_by(QDSAsset.created_at.desc())
    )
    assets = result.scalars().all()
    return [
        {"id": str(a.id), "name": a.name, "slug": a.slug,
         "status": a.status, "created_at": a.created_at.isoformat()}
        for a in assets
    ]


@router.get("/{asset_id}/resolve")
async def resolve(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    resolved = await resolve_qds(asset_id, db)
    if not resolved:
        raise HTTPException(status_code=404, detail="QDS asset not found")
    return resolved


@router.get("/{asset_id}/versions/{version_id}")
async def get_version(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QDSVersion).where(
            QDSVersion.id == version_id,
            QDSVersion.asset_id == asset_id
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": str(version.id),
        "asset_id": str(version.asset_id),
        "version_number": version.version_number,
        "review_state": version.review_state,
        "reviewed_at": version.reviewed_at.isoformat() if version.reviewed_at else None,
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "created_at": version.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Deployment endpoints — lifecycle, deploy, rollback
# ---------------------------------------------------------------------------

from app.services.qds_deployment_service import (
    transition_qds_version_state,
    deploy_qds_version,
    rollback_qds_deployment,
    list_qds_deployments,
)
from app.services.qds_runtime import start_session, get_session, submit_answer
from pydantic import BaseModel as _BaseModel
from typing import Any as _Any


class QDSStateIn(_BaseModel):
    state: str


class QDSDeployIn(_BaseModel):
    version_id: str
    environment: str
    deployed_by: str | None = None


class QDSRollbackIn(_BaseModel):
    environment: str


@router.patch("/{asset_id}/versions/{version_id}/state")
async def qds_transition_state(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    body: QDSStateIn,
    db: AsyncSession = Depends(get_db),
):
    return await transition_qds_version_state(
        asset_id=asset_id,
        version_id=version_id,
        requested_state=body.state,
        db=db,
    )


@router.post("/{asset_id}/deploy", status_code=201)
async def qds_deploy(
    asset_id: uuid.UUID,
    body: QDSDeployIn,
    db: AsyncSession = Depends(get_db),
):
    return await deploy_qds_version(
        asset_id=asset_id,
        version_id=uuid.UUID(body.version_id),
        environment=body.environment,
        deployed_by=body.deployed_by,
        db=db,
    )


@router.post("/{asset_id}/rollback")
async def qds_rollback(
    asset_id: uuid.UUID,
    body: QDSRollbackIn,
    db: AsyncSession = Depends(get_db),
):
    return await rollback_qds_deployment(
        asset_id=asset_id,
        environment=body.environment,
        db=db,
    )


@router.get("/{asset_id}/deployments")
async def qds_deployments(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await list_qds_deployments(asset_id=asset_id, db=db)


class SessionStartIn(_BaseModel):
    session_key: str
    device_metadata: dict | None = None


class AnswerSubmitIn(_BaseModel):
    session_key: str
    step_id: str
    answer_value: _Any


@router.post("/{asset_id}/sessions", status_code=201)
async def create_session(
    asset_id: uuid.UUID,
    body: SessionStartIn,
    db: AsyncSession = Depends(get_db),
):
    return await start_session(
        asset_id=asset_id,
        session_key=body.session_key,
        device_metadata=body.device_metadata,
        db=db,
    )


@router.get("/{asset_id}/sessions/{session_key}")
async def read_session(
    asset_id: uuid.UUID,
    session_key: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_session(asset_id=asset_id, session_key=session_key, db=db)


@router.post("/{asset_id}/sessions/{session_key}/answer")
async def submit_step_answer(
    asset_id: uuid.UUID,
    session_key: str,
    body: AnswerSubmitIn,
    db: AsyncSession = Depends(get_db),
):
    return await submit_answer(
        asset_id=asset_id,
        session_key=session_key,
        step_id=uuid.UUID(body.step_id),
        answer_value=body.answer_value,
        db=db,
    )
