from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.core.auth import require_api_key
from app.models.experiment import (
    Experiment, ExperimentVariant, ExperimentAssignment
)
from app.services.experiment_service import (
    create_experiment, add_variant, validate_allocation,
    transition_experiment_status, get_or_assign_variant,
)

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


class ExperimentCreateIn(BaseModel):
    asset_id: str
    asset_type: str
    experiment_name: str
    hypothesis: str | None = None
    primary_metric: str | None = None
    goal_metric: Optional[str] = None


class VariantAddIn(BaseModel):
    variant_key: str
    traffic_percentage: float
    is_control: bool = False
    surface_version_id: Optional[str] = None
    qds_version_id: Optional[str] = None


class StatusTransitionIn(BaseModel):
    status: str


class PromoteWinnerIn(BaseModel):
    variant_id: str
    environment: str = "production"
    promoted_by: str = "operator"


@router.post("", status_code=201)
async def create_experiment_route(
    body: ExperimentCreateIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    exp = await create_experiment(
        db,
        asset_id=body.asset_id,
        asset_type=body.asset_type,
        experiment_name=body.experiment_name,
        goal_metric=body.goal_metric or body.primary_metric or body.hypothesis,
    )
    return {
        "id": str(exp.id),
        "experiment_id": exp.experiment_id,
        "asset_id": str(exp.asset_id),
        "asset_type": exp.asset_type,
        "experiment_name": exp.experiment_name,
        "goal_metric": exp.goal_metric,
        "status": exp.status,
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
    }


@router.get("")
async def list_experiments(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    result = await db.execute(select(Experiment).order_by(Experiment.created_at.desc()))
    experiments = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "experiment_id": e.experiment_id,
            "asset_id": str(e.asset_id),
            "asset_type": e.asset_type,
            "experiment_name": e.experiment_name,
            "goal_metric": e.goal_metric,
            "status": e.status,
        }
        for e in experiments
    ]


@router.get("/{experiment_id}")
async def get_experiment_route(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    variants_result = await db.execute(
        select(ExperimentVariant).where(
            ExperimentVariant.experiment_id == exp.id
        )
    )
    variants = variants_result.scalars().all()

    return {
        "id": str(exp.id),
        "experiment_id": exp.experiment_id,
        "asset_id": str(exp.asset_id),
        "asset_type": exp.asset_type,
        "experiment_name": exp.experiment_name,
        "goal_metric": exp.goal_metric,
        "status": exp.status,
        "start_at": exp.start_at.isoformat() if exp.start_at else None,
        "end_at": exp.end_at.isoformat() if exp.end_at else None,
        "variants": [
            {
                "id": str(v.id),
                "variant_key": v.variant_key,
                "traffic_percentage": float(v.traffic_percentage),
                "is_control": v.is_control,
                "surface_version_id": str(v.surface_version_id) if v.surface_version_id else None,
                "qds_version_id": str(v.qds_version_id) if v.qds_version_id else None,
                "status": v.status,
            }
            for v in variants
        ],
    }


@router.post("/{experiment_id}/variants", status_code=201)
async def add_variant_route(
    experiment_id: str,
    body: VariantAddIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    try:
        variant = await add_variant(
            db,
            experiment_id=experiment_id,
            variant_key=body.variant_key,
            traffic_percentage=body.traffic_percentage,
            is_control=body.is_control,
            surface_version_id=body.surface_version_id,
            qds_version_id=body.qds_version_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "id": str(variant.id),
        "experiment_id": experiment_id,
        "variant_key": variant.variant_key,
        "traffic_percentage": float(variant.traffic_percentage),
        "is_control": variant.is_control,
        "surface_version_id": str(variant.surface_version_id) if variant.surface_version_id else None,
        "qds_version_id": str(variant.qds_version_id) if variant.qds_version_id else None,
        "status": variant.status,
    }


@router.post("/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    try:
        exp = await transition_experiment_status(db, experiment_id, "live")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"experiment_id": exp.experiment_id, "status": exp.status}


@router.post("/{experiment_id}/pause")
async def pause_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    try:
        exp = await transition_experiment_status(db, experiment_id, "paused")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"experiment_id": exp.experiment_id, "status": exp.status}


@router.post("/{experiment_id}/complete")
async def complete_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    try:
        exp = await transition_experiment_status(db, experiment_id, "complete")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"experiment_id": exp.experiment_id, "status": exp.status}


@router.get("/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    exp_result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    variants_result = await db.execute(
        select(ExperimentVariant).where(
            ExperimentVariant.experiment_id == exp.id
        )
    )
    variants = variants_result.scalars().all()

    variant_results = []
    for v in variants:
        assignments_result = await db.execute(
            select(ExperimentAssignment).where(
                ExperimentAssignment.variant_id == v.id
            )
        )
        assignments = assignments_result.scalars().all()
        session_count = len(assignments)
        variant_results.append({
            "variant_id": str(v.id),
            "variant_key": v.variant_key,
            "is_control": v.is_control,
            "traffic_percentage": float(v.traffic_percentage),
            "sessions": session_count,
            "surface_version_id": str(v.surface_version_id) if v.surface_version_id else None,
            "qds_version_id": str(v.qds_version_id) if v.qds_version_id else None,
        })

    total_sessions = sum(r["sessions"] for r in variant_results)
    for r in variant_results:
        r["traffic_share"] = round(
            r["sessions"] / total_sessions * 100, 2
        ) if total_sessions > 0 else 0.0

    return {
        "experiment_id": exp.experiment_id,
        "experiment_name": exp.experiment_name,
        "asset_id": str(exp.asset_id),
        "asset_type": exp.asset_type,
        "goal_metric": exp.goal_metric,
        "status": exp.status,
        "variant_results": variant_results,
        "total_sessions": total_sessions,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }


@router.post("/{experiment_id}/promote")
async def promote_winner(
    experiment_id: str,
    body: PromoteWinnerIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """
    Promotes the winning variant's version to production via CIF Core.
    Does not bypass governance — calls existing deploy service.
    Completes the experiment after promotion.
    """
    import uuid as _uuid

    # Load experiment
    exp_result = await db.execute(
        select(Experiment).where(
            Experiment.experiment_id == experiment_id
        )
    )
    exp = exp_result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if exp.status not in ("live", "paused"):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot promote from experiment in status: {exp.status}"
        )

    # Load variant
    variant_result = await db.execute(
        select(ExperimentVariant).where(
            ExperimentVariant.id == _uuid.UUID(body.variant_id)
        )
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.experiment_id != exp.id:
        raise HTTPException(
            status_code=422, detail="Variant does not belong to this experiment"
        )

    # Determine version and asset type, then promote via CIF Core
    deployment_result = None
    deployment_id = None
    deployment_status = "active"

    if exp.asset_type == "qds" and variant.qds_version_id:
        from app.services.qds_deployment_service import deploy_qds_version
        result_dict = await deploy_qds_version(
            asset_id=exp.asset_id,
            version_id=variant.qds_version_id,
            environment=body.environment,
            deployed_by=body.promoted_by,
            db=db,
        )
        deployment_id = result_dict.get("id")
        deployment_status = result_dict.get("status", "active")

    elif exp.asset_type == "conversion_surface" and variant.surface_version_id:
        from app.services.deployment_service import deploy_surface
        from app.models.deployment import DeploymentEnvironment
        dep, err = await deploy_surface(
            db=db,
            surface_id=exp.asset_id,
            version_id=variant.surface_version_id,
            environment=DeploymentEnvironment(body.environment),
            api_key=body.promoted_by,
        )
        if err:
            raise HTTPException(status_code=422, detail=err)
        deployment_id = str(dep.id) if dep else None
        deployment_status = dep.status.value if dep else "active"

    else:
        raise HTTPException(
            status_code=422,
            detail="Cannot determine version to promote for this asset type"
        )

    # Mark experiment complete after promotion
    try:
        await transition_experiment_status(db, experiment_id, "complete")
    except Exception:
        pass  # Do not block promotion if already complete

    # Generate insight report
    try:
        from app.models.experiment import InsightReport
        report = InsightReport(
            report_id=f"promo-{_uuid.uuid4().hex[:8]}",
            asset_id=exp.asset_id,
            experiment_id=exp.id,
            report_type="optimization_recommendation",
            title=f"Variant {variant.variant_key} promoted to {body.environment}",
            summary=(
                f"Experiment {experiment_id} completed. "
                f"Variant {variant.variant_key} was promoted to "
                f"{body.environment} by {body.promoted_by}."
            ),
            payload_json={
                "experiment_id": experiment_id,
                "promoted_variant": variant.variant_key,
                "variant_id": str(variant.id),
                "environment": body.environment,
                "promoted_by": body.promoted_by,
            },
            status="active",
        )
        db.add(report)
        await db.commit()
    except Exception:
        pass  # Insight report failure must never block promotion

    return {
        "experiment_id": experiment_id,
        "promoted_variant": variant.variant_key,
        "asset_type": exp.asset_type,
        "environment": body.environment,
        "deployment": {
            "id": deployment_id,
            "status": deployment_status,
        },
        "experiment_status": "complete",
        "promoted_by": body.promoted_by,
    }
