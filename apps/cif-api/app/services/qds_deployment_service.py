"""
QDS Deployment Service

Plugs QDS into CIF Core deployment backbone.
Mirrors surface deployment patterns exactly.
QDS does NOT reimplement lifecycle logic — it uses the same model.
"""

import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from app.models.qds import QDSAsset, QDSVersion, QDSDeployment
from app.models.experiment import Experiment


VALID_TRANSITIONS = {
    "draft": "review",
    "review": "published",
    "published": "archived",
}

VALID_ENVIRONMENTS = {"preview", "staging", "production"}


# ---------------------------------------------------------------------------
# Lifecycle — mirrors surface state machine exactly
# ---------------------------------------------------------------------------

async def transition_qds_version_state(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    requested_state: str,
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(QDSVersion).where(
            QDSVersion.id == version_id,
            QDSVersion.asset_id == asset_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="QDS version not found")

    allowed_next = VALID_TRANSITIONS.get(version.review_state)
    if allowed_next != requested_state:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transition: {version.review_state} → {requested_state}",
        )

    version.review_state = requested_state
    if requested_state == "review":
        version.reviewed_at = datetime.utcnow()
    elif requested_state == "published":
        version.published_at = datetime.utcnow()

    await db.commit()
    return {
        "version_id": str(version.id),
        "review_state": version.review_state,
        "reviewed_at": version.reviewed_at.isoformat() if version.reviewed_at else None,
        "published_at": version.published_at.isoformat() if version.published_at else None,
    }


# ---------------------------------------------------------------------------
# Deployment — mirrors surface deployment exactly
# ---------------------------------------------------------------------------

async def deploy_qds_version(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    environment: str,
    deployed_by: str | None,
    db: AsyncSession,
) -> dict:
    if environment not in VALID_ENVIRONMENTS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid environment: {environment}. Valid: {VALID_ENVIRONMENTS}",
        )

    # Confirm version exists and is published
    result = await db.execute(
        select(QDSVersion).where(
            QDSVersion.id == version_id,
            QDSVersion.asset_id == asset_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="QDS version not found")

    if version.review_state != "published":
        raise HTTPException(
            status_code=422,
            detail=f"Only published versions can be deployed. Current state: {version.review_state}",
        )

    # Deactivate any currently active deployment in this environment
    result = await db.execute(
        select(QDSDeployment).where(
            QDSDeployment.asset_id == asset_id,
            QDSDeployment.environment == environment,
            QDSDeployment.status == "active",
        )
    )
    current_active = result.scalars().all()
    for dep in current_active:
        dep.status = "inactive"
        dep.deactivated_at = datetime.utcnow()

    # Create new active deployment
    deployment = QDSDeployment(
        asset_id=asset_id,
        version_id=version_id,
        environment=environment,
        status="active",
        deployed_by=deployed_by,
        deployed_at=datetime.utcnow(),
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)

    return {
        "id": str(deployment.id),
        "asset_id": str(deployment.asset_id),
        "version_id": str(deployment.version_id),
        "environment": deployment.environment,
        "status": deployment.status,
        "deployed_by": deployment.deployed_by,
        "deployed_at": deployment.deployed_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Rollback — mirrors surface rollback exactly
# ---------------------------------------------------------------------------

async def rollback_qds_deployment(
    asset_id: uuid.UUID,
    environment: str,
    db: AsyncSession,
) -> dict:
    if environment not in VALID_ENVIRONMENTS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid environment: {environment}",
        )

    # Find current active deployment
    result = await db.execute(
        select(QDSDeployment).where(
            QDSDeployment.asset_id == asset_id,
            QDSDeployment.environment == environment,
            QDSDeployment.status == "active",
        )
    )
    current = result.scalar_one_or_none()
    if not current:
        raise HTTPException(
            status_code=422,
            detail=f"No active deployment in {environment} to roll back from",
        )

    # Find most recent inactive deployment
    result = await db.execute(
        select(QDSDeployment)
        .where(
            QDSDeployment.asset_id == asset_id,
            QDSDeployment.environment == environment,
            QDSDeployment.status == "inactive",
        )
        .order_by(QDSDeployment.deactivated_at.desc())
    )
    previous = result.scalars().first()
    if not previous:
        raise HTTPException(
            status_code=422,
            detail="No prior deployment available for rollback",
        )

    # Swap
    current.status = "inactive"
    current.deactivated_at = datetime.utcnow()
    previous.status = "active"
    previous.deactivated_at = None

    await db.commit()

    return {
        "rolled_back_from": str(current.id),
        "restored_deployment": str(previous.id),
        "restored_version_id": str(previous.version_id),
        "environment": environment,
        "status": "rollback_complete",
    }


# ---------------------------------------------------------------------------
# Active version resolution — used by QDS runtime
# ---------------------------------------------------------------------------

async def get_active_qds_version(
    asset_id: uuid.UUID,
    environment: str,
    db: AsyncSession,
) -> QDSVersion | None:
    """
    Returns the QDSVersion currently active in the given environment.
    Used by the public route and runtime to resolve the correct version.
    """
    result = await db.execute(
        select(QDSDeployment).where(
            QDSDeployment.asset_id == asset_id,
            QDSDeployment.environment == environment,
            QDSDeployment.status == "active",
        )
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        return None

    result = await db.execute(
        select(QDSVersion).where(QDSVersion.id == deployment.version_id)
    )
    return result.scalar_one_or_none()


async def list_qds_deployments(
    asset_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    result = await db.execute(
        select(QDSDeployment)
        .where(QDSDeployment.asset_id == asset_id)
        .order_by(QDSDeployment.deployed_at.desc())
    )
    deployments = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "asset_id": str(d.asset_id),
            "version_id": str(d.version_id),
            "environment": d.environment,
            "status": d.status,
            "deployed_by": d.deployed_by,
            "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
            "deactivated_at": d.deactivated_at.isoformat() if d.deactivated_at else None,
        }
        for d in deployments
    ]


async def resolve_qds_for_session(
    db: AsyncSession,
    asset_id: str,
    session_id: str,
) -> dict | None:
    """
    Resolves the QDS version for a session.
    If a live experiment exists on the asset, routes to assigned variant.
    Otherwise returns the active deployment version.
    Falls back gracefully if experiment routing fails.
    """
    from app.services.experiment_service import get_or_assign_variant

    # Check experiment routing first
    try:
        # Find a live experiment for this asset
        exp_result = await db.execute(
            select(Experiment).where(
                and_(
                    Experiment.asset_id == uuid.UUID(asset_id),
                    Experiment.status == "live",
                )
            )
        )
        exp = exp_result.scalar_one_or_none()
        if exp:
            assignment = await get_or_assign_variant(
                db, exp.experiment_id, session_id
            )
            if assignment and assignment.qds_version_id:
                # Load variant to get variant_key
                from app.models.experiment import ExperimentVariant
                v_result = await db.execute(
                    select(ExperimentVariant).where(
                        ExperimentVariant.id == assignment.variant_id
                    )
                )
                variant = v_result.scalar_one_or_none()
                return {
                    "version_id": str(assignment.qds_version_id),
                    "routed_by": "experiment",
                    "variant_key": variant.variant_key if variant else None,
                }
    except Exception:
        pass  # Fall through to active deployment

    # Standard active deployment resolution
    active = await get_active_qds_version(uuid.UUID(asset_id), "production", db)
    if not active:
        return None
    return {
        "version_id": str(active.id),
        "routed_by": "deployment",
        "variant_key": None,
    }
