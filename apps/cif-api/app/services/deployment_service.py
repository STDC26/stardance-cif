import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from app.models.surface import Surface, SurfaceVersion, ReviewState
from app.models.deployment import Deployment, DeploymentEnvironment, DeploymentStatus
from app.models.experiment import Experiment
from app.core.slugify import slugify, unique_suffix

# render_as_html — GC1 Phase 3 P3-04 — enables FORGE conversion hub deployment

_DEFAULT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'IBM Plex Mono', monospace; background: #f8f7f4; color: #1a1917; padding: 2rem; }
  h1 { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2rem; margin-bottom: 1rem; }
  .content { max-width: 800px; margin: 0 auto; }
</style>
</head>
<body>
<div class="content">
<h1>{{title}}</h1>
{{body}}
</div>
</body>
</html>"""


def render_as_html(
    surface_payload: dict,
    template: str | None = None,
    decision_context: dict | None = None,
) -> str:
    tmpl = template if template is not None else _DEFAULT_HTML_TEMPLATE
    title = surface_payload.get("title", "Stardance Surface")
    body = surface_payload.get("content", "") or surface_payload.get("body", "")
    html = tmpl.replace("{{title}}", title).replace("{{body}}", body)
    if decision_context is not None:
        html += f"\n<!-- SD-DECISION-CONTEXT: {json.dumps(decision_context)} -->"
    return html


def render_surface_as_html(
    surface_payload: dict,
    template: str | None = None,
    decision_context: dict | None = None,
) -> str:
    return render_as_html(surface_payload, template, decision_context)


# Valid state transitions
VALID_TRANSITIONS = {
    ReviewState.draft: {ReviewState.review},
    ReviewState.review: {ReviewState.published, ReviewState.draft},
    ReviewState.published: {ReviewState.archived},
    ReviewState.archived: set(),
}


async def transition_version_state(
    db: AsyncSession,
    surface_id: uuid.UUID,
    version_id: uuid.UUID,
    new_state: ReviewState,
    api_key: str,
) -> tuple[SurfaceVersion | None, str | None]:
    result = await db.execute(
        select(SurfaceVersion).where(
            SurfaceVersion.id == version_id,
            SurfaceVersion.surface_id == surface_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        return None, "Version not found"

    current = version.review_state
    if new_state not in VALID_TRANSITIONS.get(current, set()):
        return None, f"Invalid transition: {current} → {new_state}"

    now = datetime.now(timezone.utc)

    if new_state == ReviewState.published:
        # Archive currently published version for this surface
        await db.execute(
            update(SurfaceVersion)
            .where(
                SurfaceVersion.surface_id == surface_id,
                SurfaceVersion.review_state == ReviewState.published,
                SurfaceVersion.id != version_id,
            )
            .values(review_state=ReviewState.archived)
        )
        version.published_at = now

    if new_state == ReviewState.review:
        version.reviewed_at = now

    version.review_state = new_state
    await db.commit()
    await db.refresh(version)
    return version, None


async def deploy_surface(
    db: AsyncSession,
    surface_id: uuid.UUID,
    version_id: uuid.UUID,
    environment: DeploymentEnvironment,
    api_key: str,
) -> tuple[Deployment | None, str | None]:
    # Verify version exists
    version_result = await db.execute(
        select(SurfaceVersion).where(
            SurfaceVersion.id == version_id,
            SurfaceVersion.surface_id == surface_id,
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        return None, "Version not found"

    # Enforce published state for staging/production
    if environment != DeploymentEnvironment.preview:
        if version.review_state != ReviewState.published:
            return None, f"Version must be published to deploy to {environment}. Current state: {version.review_state}"

    now = datetime.now(timezone.utc)

    # Deactivate existing active deployment for this surface+environment (atomic)
    await db.execute(
        update(Deployment)
        .where(
            Deployment.surface_id == surface_id,
            Deployment.environment == environment,
            Deployment.status == DeploymentStatus.active,
        )
        .values(status=DeploymentStatus.inactive, deactivated_at=now)
    )

    # Create new deployment
    deployment = Deployment(
        surface_id=surface_id,
        surface_version_id=version_id,
        environment=environment,
        status=DeploymentStatus.active,
        deployed_by=api_key,
        deployed_at=now,
        config={},
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    return deployment, None


async def rollback_deployment(
    db: AsyncSession,
    surface_id: uuid.UUID,
    environment: DeploymentEnvironment,
    api_key: str,
) -> tuple[Deployment | None, str | None]:
    now = datetime.now(timezone.utc)

    # Find current active deployment
    active_result = await db.execute(
        select(Deployment).where(
            Deployment.surface_id == surface_id,
            Deployment.environment == environment,
            Deployment.status == DeploymentStatus.active,
        )
    )
    active = active_result.scalar_one_or_none()
    if not active:
        return None, "No active deployment found"

    # Find most recent inactive deployment (previous version)
    prev_result = await db.execute(
        select(Deployment)
        .where(
            Deployment.surface_id == surface_id,
            Deployment.environment == environment,
            Deployment.status == DeploymentStatus.inactive,
            Deployment.id != active.id,
        )
        .order_by(Deployment.deployed_at.desc())
        .limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    if not prev:
        return None, "No previous deployment available for rollback"

    # Atomic swap
    active.status = DeploymentStatus.inactive
    active.deactivated_at = now
    prev.status = DeploymentStatus.active
    prev.deployed_at = now
    prev.deployed_by = api_key

    await db.commit()
    await db.refresh(prev)
    return prev, None


async def get_active_deployment(
    db: AsyncSession,
    slug: str,
    environment: DeploymentEnvironment = DeploymentEnvironment.production,
) -> tuple[SurfaceVersion | None, Deployment | None]:
    surface_result = await db.execute(
        select(Surface).where(Surface.slug == slug)
    )
    surface = surface_result.scalar_one_or_none()
    if not surface:
        return None, None

    deployment_result = await db.execute(
        select(Deployment).where(
            Deployment.surface_id == surface.id,
            Deployment.environment == environment,
            Deployment.status == DeploymentStatus.active,
        )
    )
    deployment = deployment_result.scalar_one_or_none()
    if not deployment:
        return None, None

    version_result = await db.execute(
        select(SurfaceVersion).where(SurfaceVersion.id == deployment.surface_version_id)
    )
    version = version_result.scalar_one_or_none()
    return version, deployment


async def resolve_surface_for_session(
    db: AsyncSession,
    asset_id: str,
    session_id: str,
) -> dict | None:
    """
    Resolves the surface version for a session.
    If a live experiment exists on the asset, routes to assigned variant.
    Otherwise returns the active deployment version.
    """
    from app.services.experiment_service import get_or_assign_variant
    from app.models.experiment import ExperimentVariant

    try:
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
            if assignment and assignment.surface_version_id:
                v_result = await db.execute(
                    select(ExperimentVariant).where(
                        ExperimentVariant.id == assignment.variant_id
                    )
                )
                variant = v_result.scalar_one_or_none()
                return {
                    "version_id": str(assignment.surface_version_id),
                    "routed_by": "experiment",
                    "variant_key": variant.variant_key if variant else None,
                }
    except Exception:
        pass

    # Standard active deployment resolution
    dep_result = await db.execute(
        select(Deployment).where(
            Deployment.surface_id == uuid.UUID(asset_id),
            Deployment.environment == DeploymentEnvironment.production,
            Deployment.status == DeploymentStatus.active,
        )
    )
    deployment = dep_result.scalar_one_or_none()
    if not deployment:
        return None
    return {
        "version_id": str(deployment.surface_version_id),
        "routed_by": "deployment",
        "variant_key": None,
    }
