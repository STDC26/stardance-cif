"""A2 → FORGE pipeline (TCE-11 Path 3) — underwrite-only.

POST /api/v1/a2/pipeline
  1. Calls A2 /v1/a2/underwrite with a synthetic payload derived from the
     caller's CIF hcts_target_profile (must opt in via test_mode=True).
  2. Routes FORGE side-effects based on the A2 decision:
       AUTO_LAUNCH        → create surface + publish + deploy to production
       HUMAN_REVIEW       → create surface + publish (no deploy) + mint preview
       PAUSE_AND_DIAGNOSE → no surface
  3. Emits an ``a2_pipeline_complete`` audit signal with the full context.

OUT OF SCOPE: /v1/hub/generate (requires campaign object model that CIF
doesn't produce today — see a2_client.py for the Path 2 TODO).
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import json

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.copilot import SurfaceCreateBrief
from app.core.auth import require_api_key
from app.core.config import settings
from app.db.session import get_db
from app.models.deployment import DeploymentEnvironment
from app.models.preview import PreviewToken
from app.models.signal import EventType, SignalEvent
from app.models.surface import ReviewState
from app.schemas.surface import ComponentConfigIn, SectionIn, SurfaceCreateIn
from app.services.a2_client import a2_underwrite, a2_underwrite_raw
from app.services.cqx_sequencing_engine import sequence_surface
from app.services.deployment_service import (
    deploy_surface as deploy_surface_service,
    transition_version_state,
)
from app.services.stage_profiler import build_stage_profiles
from app.services.surface_service import create_surface as create_surface_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/a2", tags=["a2"])


_RENDERER_BASE = "https://sd-chubs-renderer.vercel.app"


# ── Request model ──────────────────────────────────────────────────────────


class A2PipelineBody(BaseModel):
    brand_id: str
    hcts_target_profile: dict[str, Any]
    surface_brief: Optional[SurfaceCreateBrief] = None
    test_mode: bool = False


# ── Signal emission (best-effort) ──────────────────────────────────────────


def _emit_pipeline_complete_signal(
    db: AsyncSession,
    surface_id: Optional[Any],
    version_id: Optional[Any],
    metadata: dict,
) -> None:
    try:
        db.add(SignalEvent(
            surface_id=surface_id,
            event_type=EventType.a2_pipeline_complete,
            event_data={
                **metadata,
                "surface_version_id": str(version_id) if version_id else None,
            },
        ))
    except Exception as e:
        logger.warning("a2_pipeline_complete signal emission failed: %s", e)


# ── Helpers for surface creation under a specific routing decision ─────────


async def _create_and_publish_surface(
    db: AsyncSession,
    brief: SurfaceCreateBrief,
    api_key: str,
) -> tuple[Any, Any]:
    """CQX → create → review → publish. Returns (surface, version).

    Used by both AUTO_LAUNCH (followed by deploy) and HUMAN_REVIEW
    (followed by preview-token mint). Raises HTTPException on failure.
    """
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
    return surface, version


def _mint_preview(
    db: AsyncSession,
    surface_id: Any,
    surface_slug: str,
    version_id: Any,
    api_key: str,
) -> tuple[str, str]:
    secret = secrets.token_urlsafe(16)
    preview_id = f"prev-{secret[:8]}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    db.add(PreviewToken(
        preview_id=preview_id,
        asset_id=surface_id,
        asset_type="conversion_surface",
        asset_slug=surface_slug,
        version_id=version_id,
        expires_at=expires_at,
        created_by=api_key,
    ))
    preview_url = f"{_RENDERER_BASE}/?slug={surface_slug}&preview={preview_id}"
    return preview_id, preview_url


# ── Endpoint ───────────────────────────────────────────────────────────────


@router.post("/pipeline")
async def a2_pipeline(
    body: A2PipelineBody,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Underwrite via A2, then route FORGE side-effects by A2 decision."""
    pipeline_start = time.monotonic()

    if not body.test_mode:
        # Path 3 requires the caller to acknowledge that the A2 payload is
        # synthesised from CIF HCTS rather than produced by a real campaign
        # scoring pipeline. Remove this gate once Path 2 lands.
        raise HTTPException(
            status_code=422,
            detail={
                "error": "test_mode_required",
                "reason": (
                    "Path 3 uses synthetic A2 inputs derived from HCTS. "
                    "Set test_mode=true to acknowledge."
                ),
            },
        )

    # 1. A2 underwrite
    try:
        underwrite = await a2_underwrite(body.brand_id, body.hcts_target_profile)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "a2_underwrite_failed",
                "status": e.response.status_code if e.response else None,
                "detail": e.response.text[:500] if e.response else str(e),
                "brand_id": body.brand_id,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "a2_underwrite_failed",
                "detail": str(e),
                "brand_id": body.brand_id,
            },
        )

    decision: str = underwrite.get("decision", "PAUSE_AND_DIAGNOSE")
    system_fit = underwrite.get("system_fit")
    system_confidence = underwrite.get("system_confidence")
    calibration_event_id = underwrite.get("calibration_event_id")
    triggered_penalties = underwrite.get("triggered_penalties") or []
    decision_rationale = underwrite.get("decision_rationale") or []
    a2_latency_ms = underwrite.get("_latency_ms")

    # 2. FORGE routing based on decision
    surface_created = False
    slug: Optional[str] = None
    surface_uuid: Optional[Any] = None
    version_uuid: Optional[Any] = None
    deployment_id: Optional[str] = None
    preview_id: Optional[str] = None
    preview_url: Optional[str] = None
    gate_blocked = False
    block_reason: Optional[str] = None

    # Known A2 decisions:
    #   AUTO_LAUNCH        → deploy surface (if brief provided)
    #   HUMAN_REVIEW       → create draft + mint preview token
    #   PAUSE_AND_DIAGNOSE → gate_blocked, no surface
    #   NO_LAUNCH          → gate_blocked, no surface (hard stop, no review)
    if decision in ("PAUSE_AND_DIAGNOSE", "NO_LAUNCH"):
        gate_blocked = True
        block_reason = (
            decision_rationale[0] if decision_rationale
            else f"A2 decision: {decision}"
        )

    elif decision == "AUTO_LAUNCH":
        if body.surface_brief is not None:
            surface, version = await _create_and_publish_surface(
                db, body.surface_brief, api_key,
            )
            deployment, err = await deploy_surface_service(
                db, surface.id, version.id,
                DeploymentEnvironment.production, api_key,
            )
            if deployment is None:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "deploy_failed", "failure_reason": err},
                )
            surface_created = True
            slug = surface.slug
            surface_uuid = surface.id
            version_uuid = version.id
            deployment_id = str(deployment.id)

    elif decision == "HUMAN_REVIEW":
        if body.surface_brief is not None:
            surface, version = await _create_and_publish_surface(
                db, body.surface_brief, api_key,
            )
            preview_id, preview_url = _mint_preview(
                db, surface.id, surface.slug, version.id, api_key,
            )
            surface_created = True
            slug = surface.slug
            surface_uuid = surface.id
            version_uuid = version.id

    else:
        # Any decision outside the known four — treat as a block, log loudly.
        logger.warning("a2_pipeline: unexpected decision=%r", decision)
        gate_blocked = True
        block_reason = f"Unknown A2 decision: {decision!r}"

    # 3. Audit log
    _emit_pipeline_complete_signal(
        db, surface_uuid, version_uuid,
        {
            "brand_id": body.brand_id,
            "a2_decision": decision,
            "system_fit": system_fit,
            "system_confidence": system_confidence,
            "surface_created": surface_created,
            "slug": slug,
            "test_mode": True,
            "calibration_event_id": calibration_event_id,
            "triggered_penalties": triggered_penalties,
        },
    )

    await db.commit()
    pipeline_latency_ms = int((time.monotonic() - pipeline_start) * 1000)

    return {
        "a2_decision": decision,
        "system_fit": system_fit,
        "system_confidence": system_confidence,
        "calibration_event_id": calibration_event_id,
        "triggered_penalties": triggered_penalties,
        "decision_rationale": decision_rationale,
        "surface_created": surface_created,
        "slug": slug,
        "deployment_id": deployment_id,
        "preview_id": preview_id,
        "preview_url": preview_url,
        "gate_blocked": gate_blocked,
        "block_reason": block_reason,
        "test_mode": True,
        "a2_latency_ms": a2_latency_ms,
        "pipeline_latency_ms": pipeline_latency_ms,
    }


# ── TCE-15 — real BASE → A2 pipeline ────────────────────────────────────────


@router.post("/pipeline/measured")
async def a2_pipeline_measured(
    image_file: UploadFile = File(...),
    video_file: UploadFile = File(...),
    landing_page_file: UploadFile = File(...),
    brand_id: str = Form(...),
    sector: str = Form("BEAUTY_SKINCARE"),
    brand_context: Optional[str] = Form(None),
    surface_brief: Optional[str] = Form(None),
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Real BASE → A2 pipeline — replaces the synthetic test_mode path.

    Three assets (image / video / landing_page) flow through BASE to
    produce per-stage NinePDProfiles, then into A2 for the real decision.
    """
    pipeline_start = time.monotonic()

    # 0. Read form inputs
    image_bytes = await image_file.read()
    video_bytes = await video_file.read()
    lp_bytes = await landing_page_file.read()

    try:
        brand_ctx = json.loads(brand_context) if brand_context else {"brand_id": brand_id}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_brand_context_json"},
        )

    try:
        brief_obj: Optional[SurfaceCreateBrief] = (
            SurfaceCreateBrief(**json.loads(surface_brief))
            if surface_brief else None
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_surface_brief", "detail": str(e)},
        )

    # 1. BASE measurements — stage profiles + derived fields
    try:
        a2_inputs = await build_stage_profiles(
            image_bytes, video_bytes, lp_bytes,
            brand_ctx,
            settings.BASE_API_KEY or None,
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail={"error": "base_measurement_timeout", "detail": str(e)},
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "base_measurement_failed",
                "status": e.response.status_code if e.response else None,
                "detail": e.response.text[:500] if e.response else str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"error": "base_measurement_failed", "detail": str(e)},
        )

    lineage = a2_inputs.pop("_lineage", {})

    # 2. A2 underwrite with the measured payload
    a2_payload = {
        "brand_id": brand_id,
        "sector": sector,
        **a2_inputs,
    }
    try:
        underwrite = await a2_underwrite_raw(a2_payload)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "a2_underwrite_failed",
                "status": e.response.status_code if e.response else None,
                "detail": e.response.text[:500] if e.response else str(e),
                "brand_id": brand_id,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"error": "a2_underwrite_failed", "detail": str(e), "brand_id": brand_id},
        )

    decision: str = underwrite.get("decision", "NO_LAUNCH")
    system_fit = underwrite.get("system_fit")
    system_confidence = underwrite.get("system_confidence")
    calibration_event_id = underwrite.get("calibration_event_id")
    triggered_penalties = underwrite.get("triggered_penalties") or []
    decision_rationale = underwrite.get("decision_rationale") or []
    a2_latency_ms = underwrite.get("_latency_ms")

    # 3. FORGE routing (mirrors /pipeline test_mode routing)
    surface_created = False
    slug: Optional[str] = None
    surface_uuid: Optional[Any] = None
    version_uuid: Optional[Any] = None
    deployment_id: Optional[str] = None
    preview_id: Optional[str] = None
    preview_url: Optional[str] = None
    gate_blocked = False
    block_reason: Optional[str] = None

    if decision in ("PAUSE_AND_DIAGNOSE", "NO_LAUNCH"):
        gate_blocked = True
        block_reason = (
            decision_rationale[0] if decision_rationale
            else f"A2 decision: {decision}"
        )
    elif decision == "AUTO_LAUNCH":
        if brief_obj is not None:
            surface, version = await _create_and_publish_surface(db, brief_obj, api_key)
            deployment, err = await deploy_surface_service(
                db, surface.id, version.id,
                DeploymentEnvironment.production, api_key,
            )
            if deployment is None:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "deploy_failed", "failure_reason": err},
                )
            surface_created = True
            slug = surface.slug
            surface_uuid = surface.id
            version_uuid = version.id
            deployment_id = str(deployment.id)
    elif decision == "HUMAN_REVIEW":
        if brief_obj is not None:
            surface, version = await _create_and_publish_surface(db, brief_obj, api_key)
            preview_id, preview_url = _mint_preview(
                db, surface.id, surface.slug, version.id, api_key,
            )
            surface_created = True
            slug = surface.slug
            surface_uuid = surface.id
            version_uuid = version.id
    else:
        logger.warning("a2_pipeline_measured: unexpected decision=%r", decision)
        gate_blocked = True
        block_reason = f"Unknown A2 decision: {decision!r}"

    # 4. Audit log with measurement lineage
    _emit_pipeline_complete_signal(
        db, surface_uuid, version_uuid,
        {
            "brand_id": brand_id,
            "a2_decision": decision,
            "system_fit": system_fit,
            "system_confidence": system_confidence,
            "surface_created": surface_created,
            "slug": slug,
            "test_mode": False,
            "measurement_source": "BASE",
            "calibration_event_id": calibration_event_id,
            "triggered_penalties": triggered_penalties,
            "lineage": lineage,
        },
    )

    await db.commit()
    pipeline_latency_ms = int((time.monotonic() - pipeline_start) * 1000)

    return {
        "a2_decision": decision,
        "system_fit": system_fit,
        "system_confidence": system_confidence,
        "calibration_event_id": calibration_event_id,
        "triggered_penalties": triggered_penalties,
        "decision_rationale": decision_rationale,
        "surface_created": surface_created,
        "slug": slug,
        "deployment_id": deployment_id,
        "preview_id": preview_id,
        "preview_url": preview_url,
        "gate_blocked": gate_blocked,
        "block_reason": block_reason,
        "measurement_source": "BASE",
        "test_mode": False,
        "lineage": {
            **lineage,
            "stage_profiles": a2_inputs.get("stage_profiles"),
            "stage_fits": a2_inputs.get("stage_fits"),
            "stage_confidences": a2_inputs.get("stage_confidences"),
            "stage_gates_passed": a2_inputs.get("stage_gates_passed"),
            "measurement_quality": a2_inputs.get("measurement_quality"),
        },
        "a2_latency_ms": a2_latency_ms,
        "pipeline_latency_ms": pipeline_latency_ms,
    }
