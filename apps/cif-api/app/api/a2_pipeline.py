"""A2 → FORGE pipeline orchestration (TCE-11).

Single POST /api/v1/a2/pipeline that:
  1. Underwrites the brand via A2
  2. If the decision is AUTO_LAUNCH or HUMAN_REVIEW, calls hub/generate
  3. On AUTO_LAUNCH + gate_pass, runs the full FORGE create+deploy pipeline
  4. On HUMAN_REVIEW + gate_pass, creates + publishes the surface and mints
     a preview token (no production deploy)
  5. On gate_pass=False OR PAUSE_AND_DIAGNOSE, returns gate_blocked without
     creating a surface

Routing via public A2 URL (Option B). See app/services/a2_client.py for the
Option A migration note.
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.copilot import SurfaceCreateBrief
from app.core.auth import require_api_key
from app.db.session import get_db
from app.models.deployment import DeploymentEnvironment
from app.models.preview import PreviewToken
from app.models.signal import EventType, SignalEvent
from app.models.surface import ReviewState
from app.schemas.surface import ComponentConfigIn, SectionIn, SurfaceCreateIn
from app.services.a2_client import a2_hub_generate, a2_underwrite
from app.services.cqx_sequencing_engine import sequence_surface
from app.services.deployment_service import (
    deploy_surface as deploy_surface_service,
    transition_version_state,
)
from app.services.surface_service import create_surface as create_surface_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/a2", tags=["a2"])


_RENDERER_BASE = "https://sd-chubs-renderer.vercel.app"


# ── Request / response models ───────────────────────────────────────────────


class A2PipelineBody(BaseModel):
    brand_context: dict[str, Any]
    surface_brief: SurfaceCreateBrief
    auto_launch: bool = True


# ── Signal emission helper ─────────────────────────────────────────────────


def _emit_pipeline_signal(
    db: AsyncSession,
    surface_id: Optional[str],
    version_id: Optional[str],
    event_data: dict,
) -> None:
    try:
        db.add(SignalEvent(
            surface_id=surface_id if surface_id else None,
            event_type=EventType.auto_launch,
            event_data={
                **event_data,
                "source": "a2_pipeline",
                "surface_version_id": version_id,
            },
        ))
    except Exception as e:
        logger.warning("a2_pipeline signal emission failed: %s", e)


# ── Pipeline ───────────────────────────────────────────────────────────────


@router.post("/pipeline")
async def a2_pipeline(
    body: A2PipelineBody,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Brief → A2 underwrite → hub gate → FORGE deploy in one call."""
    pipeline_start = time.monotonic()

    # 1. A2 underwrite
    try:
        underwrite = await a2_underwrite(body.brand_context)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "a2_underwrite_failed",
                "status": e.response.status_code if e.response else None,
                "detail": e.response.text[:500] if e.response else str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"error": "a2_underwrite_failed", "detail": str(e)},
        )

    decision = underwrite.get("decision")
    calibration_event_id = underwrite.get("calibration_event_id")
    a2_latency_ms = underwrite.get("_latency_ms")

    # 2. If the decision permits it, call hub/generate
    hub: dict[str, Any] = {}
    hub_latency_ms: Optional[int] = None
    if decision in ("AUTO_LAUNCH", "HUMAN_REVIEW"):
        if not calibration_event_id:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "a2_missing_calibration_event_id",
                    "underwrite": underwrite,
                },
            )
        try:
            hub = await a2_hub_generate(calibration_event_id, body.brand_context)
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "a2_hub_generate_failed",
                    "status": e.response.status_code if e.response else None,
                    "detail": e.response.text[:500] if e.response else str(e),
                    "calibration_event_id": calibration_event_id,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "a2_hub_generate_failed",
                    "detail": str(e),
                    "calibration_event_id": calibration_event_id,
                },
            )
        hub_latency_ms = hub.get("_latency_ms")

    gate_pass = bool(hub.get("gate_pass")) if hub else False
    routing_band = hub.get("routing_band")
    hub_id = hub.get("hub_id")

    # 3. Gate-blocked paths — do not create a surface
    if decision == "PAUSE_AND_DIAGNOSE" or (
        decision in ("AUTO_LAUNCH", "HUMAN_REVIEW") and not gate_pass
    ):
        _emit_pipeline_signal(db, None, None, {
            "a2_decision": decision,
            "gate_pass": gate_pass,
            "calibration_event_id": calibration_event_id,
            "hub_id": hub_id,
            "routing_band": routing_band,
            "gate_blocked": True,
        })
        await db.commit()
        pipeline_latency_ms = int((time.monotonic() - pipeline_start) * 1000)
        return {
            "a2_decision": decision,
            "calibration_event_id": calibration_event_id,
            "hub_id": hub_id,
            "routing_band": routing_band,
            "gate_pass": gate_pass,
            "surface_created": False,
            "slug": None,
            "deployment_id": None,
            "preview_id": None,
            "gate_blocked": True,
            "reason": (
                "A2 decision PAUSE_AND_DIAGNOSE"
                if decision == "PAUSE_AND_DIAGNOSE"
                else "hub gate_pass=False"
            ),
            "a2_latency_ms": a2_latency_ms,
            "hub_latency_ms": hub_latency_ms,
            "pipeline_latency_ms": pipeline_latency_ms,
        }

    # 4. Build + persist the surface (shared by AUTO_LAUNCH and HUMAN_REVIEW paths)
    brief = body.surface_brief

    # Fold brand_context.hcts_target_profile into the brief if not provided
    if not brief.hcts_target_profile and body.brand_context.get("hcts_target_profile"):
        brief.hcts_target_profile = body.brand_context["hcts_target_profile"]

    seq = sequence_surface(
        hcts_profile=brief.hcts_target_profile or {},
        scss_position=brief.scss_position,
        cqx_intensity=brief.cqx_intensity,
        components=brief.components,
    )
    if seq.validation != "PASS":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "cqx_validation_failed",
                "failure_reason": seq.failure_reason,
                "failure_mode": seq.failure_mode,
                "stage_coverage": seq.stage_coverage,
            },
        )

    try:
        sections = [SectionIn(
            section_id="main",
            components=[ComponentConfigIn(**c) for c in seq.component_sequence],
        )]
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "component_validation_failed", "failure_reason": str(e)},
        )

    surface_in = SurfaceCreateIn(
        name=brief.name,
        description=brief.description,
        type="conversion_surface",
        sections=sections,
        scss_position=brief.scss_position,
        hcts_target_profile=brief.hcts_target_profile,
        cqx_intensity=brief.cqx_intensity,
    )
    surface, version = await create_surface_service(db, surface_in)
    if surface is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "surface_create_failed", "failure_reason": version},
        )

    reviewed, err = await transition_version_state(
        db, surface.id, version.id, ReviewState.review, api_key,
    )
    if reviewed is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "review_transition_failed", "failure_reason": err},
        )
    published, err = await transition_version_state(
        db, surface.id, version.id, ReviewState.published, api_key,
    )
    if published is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "publish_transition_failed", "failure_reason": err},
        )

    # 5. Deploy or mint preview based on A2 decision
    deployment_id: Optional[str] = None
    preview_id: Optional[str] = None
    preview_url: Optional[str] = None

    if decision == "AUTO_LAUNCH" and body.auto_launch:
        deployment, err = await deploy_surface_service(
            db, surface.id, version.id,
            DeploymentEnvironment.production, api_key,
        )
        if deployment is None:
            raise HTTPException(
                status_code=422,
                detail={"error": "deploy_failed", "failure_reason": err},
            )
        deployment_id = str(deployment.id)
    else:
        # HUMAN_REVIEW (or AUTO_LAUNCH with auto_launch=False) — mint preview token
        secret = secrets.token_urlsafe(16)
        preview_id = f"prev-{secret[:8]}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        db.add(PreviewToken(
            preview_id=preview_id,
            asset_id=surface.id,
            asset_type="conversion_surface",
            asset_slug=surface.slug,
            version_id=version.id,
            expires_at=expires_at,
            created_by=api_key,
        ))
        preview_url = f"{_RENDERER_BASE}/?slug={surface.slug}&preview={preview_id}"

    _emit_pipeline_signal(db, str(surface.id), str(version.id), {
        "a2_decision": decision,
        "gate_pass": gate_pass,
        "calibration_event_id": calibration_event_id,
        "hub_id": hub_id,
        "routing_band": routing_band,
        "slug": surface.slug,
        "deployment_id": deployment_id,
        "preview_id": preview_id,
    })

    await db.commit()
    pipeline_latency_ms = int((time.monotonic() - pipeline_start) * 1000)

    return {
        "a2_decision": decision,
        "calibration_event_id": calibration_event_id,
        "hub_id": hub_id,
        "routing_band": routing_band,
        "gate_pass": gate_pass,
        "surface_created": True,
        "slug": surface.slug,
        "surface_id": str(surface.id),
        "version_id": str(version.id),
        "deployment_id": deployment_id,
        "preview_id": preview_id,
        "preview_url": preview_url,
        "a2_latency_ms": a2_latency_ms,
        "hub_latency_ms": hub_latency_ms,
        "pipeline_latency_ms": pipeline_latency_ms,
    }
