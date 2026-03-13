"""
CIF Asset Index — Phase-6 Sprint-3

Retrieves asset metadata, version history, and deployment state.
Queries: surfaces, surface_versions, deployments tables.
READ-ONLY.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.surface import Surface, SurfaceVersion
from app.models.deployment import Deployment

logger = logging.getLogger(__name__)


async def get_asset_context(
    db: AsyncSession,
    asset_id: Optional[UUID] = None,
    slug: Optional[str] = None,
    limit_versions: int = 3,
) -> dict:
    """
    Returns asset metadata, recent versions, and deployment state.
    Accepts either asset_id or slug.
    Returns empty dict if asset not found.
    """
    try:
        # Resolve asset (Surface)
        if asset_id:
            result = await db.execute(
                select(Surface).where(Surface.id == asset_id)
            )
        elif slug:
            result = await db.execute(
                select(Surface).where(Surface.slug == slug)
            )
        else:
            return {}

        asset = result.scalar_one_or_none()
        if not asset:
            return {}

        # Get recent surface versions
        versions_result = await db.execute(
            select(SurfaceVersion)
            .where(SurfaceVersion.surface_id == asset.id)
            .order_by(desc(SurfaceVersion.created_at))
            .limit(limit_versions)
        )
        versions = versions_result.scalars().all()

        # Get active deployment
        deployment_result = await db.execute(
            select(Deployment)
            .where(
                Deployment.surface_id == asset.id,
                Deployment.status == "active",
            )
            .limit(1)
        )
        active_deployment = deployment_result.scalar_one_or_none()

        return {
            "asset_id": str(asset.id),
            "name": asset.name,
            "slug": asset.slug,
            "asset_type": asset.type,
            "status": asset.status,
            "version_count": len(versions),
            "latest_version": versions[0].version_number if versions else None,
            "active_deployment": str(active_deployment.id)
            if active_deployment else None,
            "deployed_version": active_deployment.surface_version_id
            if active_deployment else None,
        }

    except Exception as e:
        logger.error("asset_index.get_asset_context error: %s", str(e))
        return {"error": str(e)}
