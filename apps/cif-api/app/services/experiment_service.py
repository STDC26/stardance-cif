"""
Experiment Service — Phase-5
Manages experiment lifecycle, variant registration,
and deterministic session assignment.
"""

import hashlib
import uuid
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.experiment import (
    Experiment, ExperimentVariant, ExperimentAssignment
)

VALID_TRANSITIONS = {
    "draft": ["live"],
    "live": ["paused", "complete"],
    "paused": ["live", "complete"],
    "complete": ["archived"],
    "archived": [],
}


async def create_experiment(
    db: AsyncSession,
    asset_id: str,
    asset_type: str,
    experiment_name: str,
    goal_metric: Optional[str] = None,
) -> Experiment:
    exp = Experiment(
        experiment_id=f"exp-{uuid.uuid4().hex[:8]}",
        asset_id=uuid.UUID(asset_id),
        asset_type=asset_type,
        experiment_name=experiment_name,
        goal_metric=goal_metric,
        status="draft",
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


async def add_variant(
    db: AsyncSession,
    experiment_id: str,
    variant_key: str,
    traffic_percentage: float,
    is_control: bool = False,
    surface_version_id: Optional[str] = None,
    qds_version_id: Optional[str] = None,
) -> ExperimentVariant:
    if not surface_version_id and not qds_version_id:
        raise ValueError("One of surface_version_id or qds_version_id required")
    if surface_version_id and qds_version_id:
        raise ValueError("Only one version type allowed per variant")

    exp_result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise ValueError(f"Experiment {experiment_id} not found")

    variant = ExperimentVariant(
        experiment_id=exp.id,
        variant_key=variant_key,
        traffic_percentage=traffic_percentage,
        is_control=is_control,
        surface_version_id=uuid.UUID(surface_version_id) if surface_version_id else None,
        qds_version_id=uuid.UUID(qds_version_id) if qds_version_id else None,
        status="active",
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant


async def validate_allocation(
    db: AsyncSession, experiment_id: str
) -> bool:
    """Returns True if active variant allocations sum to 100."""
    exp_result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        return False

    variant_result = await db.execute(
        select(ExperimentVariant).where(
            and_(
                ExperimentVariant.experiment_id == exp.id,
                ExperimentVariant.status == "active",
            )
        )
    )
    variants = variant_result.scalars().all()
    total = sum(float(v.traffic_percentage) for v in variants)
    return abs(total - 100.0) < 0.01


async def transition_experiment_status(
    db: AsyncSession, experiment_id: str, new_status: str
) -> Experiment:
    exp_result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise ValueError(f"Experiment {experiment_id} not found")

    allowed = VALID_TRANSITIONS.get(exp.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Invalid transition: {exp.status} → {new_status}"
        )

    if new_status == "live":
        valid = await validate_allocation(db, experiment_id)
        if not valid:
            raise ValueError(
                "Cannot go live: variant traffic allocations must sum to 100%"
            )

    exp.status = new_status
    await db.commit()
    await db.refresh(exp)
    return exp


async def get_or_assign_variant(
    db: AsyncSession,
    experiment_id: str,
    session_id: str,
    anonymous_user_id: Optional[str] = None,
) -> ExperimentAssignment:
    """Deterministically assign a session to a variant using consistent hashing."""
    exp_result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise ValueError(f"Experiment {experiment_id} not found")
    if exp.status != "live":
        raise ValueError(f"Experiment is not live (status={exp.status})")

    # Check for existing assignment
    existing = await db.execute(
        select(ExperimentAssignment).where(
            and_(
                ExperimentAssignment.experiment_id == exp.id,
                ExperimentAssignment.session_id == session_id,
            )
        )
    )
    existing_assignment = existing.scalar_one_or_none()
    if existing_assignment:
        return existing_assignment

    # Get active variants sorted by key for determinism
    variant_result = await db.execute(
        select(ExperimentVariant).where(
            and_(
                ExperimentVariant.experiment_id == exp.id,
                ExperimentVariant.status == "active",
            )
        ).order_by(ExperimentVariant.variant_key)
    )
    variants = variant_result.scalars().all()
    if not variants:
        raise ValueError("No active variants for experiment")

    # Deterministic assignment via consistent hash
    hash_input = f"{experiment_id}:{session_id}"
    hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
    bucket = hash_value % 10000  # 0–9999 for 0.01% precision

    cumulative = 0.0
    chosen_variant = variants[-1]  # fallback
    for v in variants:
        cumulative += float(v.traffic_percentage) * 100  # percentage → basis points
        if bucket < cumulative:
            chosen_variant = v
            break

    assignment = ExperimentAssignment(
        experiment_id=exp.id,
        variant_id=chosen_variant.id,
        session_id=session_id,
        anonymous_user_id=anonymous_user_id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def get_experiment(
    db: AsyncSession, experiment_id: str
) -> Optional[Experiment]:
    result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    return result.scalar_one_or_none()


async def list_experiments(
    db: AsyncSession, asset_id: Optional[str] = None
) -> list[Experiment]:
    query = select(Experiment)
    if asset_id:
        query = query.where(Experiment.asset_id == uuid.UUID(asset_id))
    query = query.order_by(Experiment.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
