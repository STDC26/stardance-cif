"""
CIF Copilot API — Phase-6 Sprint-5

Exposes AI-assisted draft generation endpoints.
All endpoints return drafts with status="draft".
No platform state changes — drafts are returned, not persisted.
"""

import asyncio
import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.db.session import AsyncSessionLocal, get_db
from app.models.deployment import DeploymentEnvironment
from app.models.preview import PreviewToken
from app.models.signal import EventType, SignalEvent
from app.models.surface import ReviewState
from app.schemas.surface import ComponentConfigIn, SectionIn, SurfaceCreateIn
from app.services.ai_provider.external_llm_client import call_external
from app.services.copilot import (
    generate_draft,
    CopilotRequest,
    CopilotAction,
)
from app.services.cqx_sequencing_engine import sequence_surface
from app.services.deployment_service import (
    deploy_surface as deploy_surface_service,
    transition_version_state,
)
from app.services.retrieval import RetrievalRequest, build_context
from app.services.surface_service import create_surface as create_surface_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


class SurfaceDraftBody(BaseModel):
    slug: Optional[str] = None
    asset_id: Optional[UUID] = None
    brief: Optional[str] = None


class QDSDraftBody(BaseModel):
    slug: Optional[str] = None
    qds_asset_id: Optional[UUID] = None
    brief: Optional[str] = None


class VariantBody(BaseModel):
    experiment_id: UUID
    asset_id: Optional[UUID] = None
    brief: Optional[str] = None


class ExperimentRecBody(BaseModel):
    slug: Optional[str] = None
    asset_id: Optional[UUID] = None
    brief: Optional[str] = None


@router.get("/health")
async def copilot_health(_: str = Depends(require_api_key)):
    """Confirms Copilot services are available."""
    return {
        "status": "ok",
        "layer": "copilot",
        "services": [
            "surface_draft_generator",
            "qds_draft_generator",
            "variant_generator",
            "experiment_recommender",
        ],
        "copilot_router": "active",
    }


@router.post("/surface-draft")
async def surface_draft(
    body: SurfaceDraftBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an AI-assisted surface draft.
    Optionally grounded in existing asset context.
    """
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.SURFACE_DRAFT,
            slug=body.slug,
            asset_id=body.asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/qds-draft")
async def qds_draft(
    body: QDSDraftBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an AI-assisted QDS diagnostic flow draft.
    Optionally grounded in existing QDS context.
    """
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.QDS_DRAFT,
            slug=body.slug,
            qds_asset_id=body.qds_asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/variants")
async def variant_suggestions(
    body: VariantBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates AI-assisted variant suggestions for an experiment.
    Grounded in existing experiment and signal context.
    """
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.VARIANT_SUGGESTION,
            experiment_id=body.experiment_id,
            asset_id=body.asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/experiment-recommendations")
async def experiment_recommendations(
    body: ExperimentRecBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates AI-assisted experiment recommendations for an asset.
    Grounded in asset performance, signals, and existing experiments.
    """
    if not body.slug and not body.asset_id:
        raise HTTPException(
            status_code=422,
            detail="slug or asset_id required",
        )
    result = await generate_draft(
        request=CopilotRequest(
            action=CopilotAction.EXPERIMENT_RECOMMENDATION,
            slug=body.slug,
            asset_id=body.asset_id,
            brief=body.brief,
        ),
        db=db,
    )
    if result.get("error") and not result.get("draft"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# TCE-07 — template-driven copilot endpoints
# Route directly to sd-llm-service via call_external() with explicit
# prompt_id overrides. The remote prompt templates are the source of truth
# for output shape; this layer only populates template variables.
# ---------------------------------------------------------------------------


class ExperimentRecommendBody(BaseModel):
    asset_id: str
    asset_type: str
    asset_name: str
    performance_summary: str
    component_summary: str


class VariantGenerateBody(BaseModel):
    component_type: str
    original_content: dict
    brand_context: str
    variant_count: int = Field(default=3, ge=1, le=10)


def _parse_list_response(
    raw: str,
    list_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    prompt_id: Optional[str] = None,
    task_type: Optional[str] = None,
) -> list:
    """Extract a JSON array from the LLM response.

    Accepts: a raw JSON array, an object with ``list_key`` holding the array,
    or either wrapped in ```json fences. Returns [] on failure.

    Empty-list fallbacks emit a ``parse_list_response_empty`` WARNING with
    the endpoint/prompt_id/task_type context and a parse_failure_reason so
    prod can diagnose why the LLM reply didn't decode to a list.
    """
    def _empty(reason: str) -> list:
        logger.warning(
            "parse_list_response_empty",
            extra={
                "endpoint": endpoint,
                "prompt_id": prompt_id,
                "task_type": task_type,
                "raw_response_truncated": raw[:200] if raw else None,
                "parse_failure_reason": reason,
            },
        )
        return []

    if not raw:
        return _empty("empty_raw_response")
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        return _empty(f"json_decode_error: {e}")
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        if list_key and isinstance(parsed.get(list_key), list):
            return parsed[list_key]
        for v in parsed.values():
            if isinstance(v, list):
                return v
        return _empty(
            f"no_list_in_object: keys={sorted(parsed.keys())[:10]}"
        )
    return _empty(f"unsupported_type: {type(parsed).__name__}")


@router.post("/experiment-recommend")
async def experiment_recommend(
    body: ExperimentRecommendBody,
    _: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    TCE-07 — AI experiment recommendations via cif.experiment-recommend prompt.

    Enriches the request body with fresh asset data from WS-G when asset_id
    resolves, then calls sd-llm-service with template variables populated.
    """
    asset_name = body.asset_name
    performance_summary = body.performance_summary
    component_summary = body.component_summary

    # Prefer DB-derived values when the asset_id resolves
    try:
        asset_uuid = UUID(body.asset_id)
    except (ValueError, AttributeError):
        asset_uuid = None

    if asset_uuid is not None:
        try:
            context = await build_context(
                request=RetrievalRequest(
                    asset_id=asset_uuid,
                    include_signals=True,
                    include_experiment=False,
                ),
                db=db,
            )
            if context:
                asset_name = context.get("asset_name") or asset_name
                signal_count = context.get("signal_total_events", 0) or 0
                is_deployed = bool(context.get("asset_deployed_version"))
                performance_summary = (
                    f"total_signals: {signal_count}, deployed: {is_deployed}"
                )
        except Exception as e:
            logger.warning(
                "experiment-recommend: DB enrichment failed for %s — %s",
                body.asset_id, e,
            )

    variables: dict[str, Any] = {
        "asset_name": asset_name,
        "performance_summary": performance_summary,
        "component_summary": component_summary,
    }

    t0 = time.monotonic()
    try:
        raw = await call_external(
            prompt="",
            task_type="recommend",
            variables=variables,
            prompt_id="cif.experiment-recommend",
        )
    except Exception as e:
        logger.error("experiment-recommend: LLM call failed: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    latency_ms = int((time.monotonic() - t0) * 1000)

    recommendations = _parse_list_response(
        raw,
        list_key="experiments",
        endpoint="/api/v1/copilot/experiment-recommend",
        prompt_id="cif.experiment-recommend",
        task_type="recommend",
    )

    return {
        "recommendations": recommendations,
        "raw_response": raw,
        "asset_id": body.asset_id,
        "latency_ms": latency_ms,
    }


@router.post("/variant-generate")
async def variant_generate(
    body: VariantGenerateBody,
    _: str = Depends(require_api_key),
):
    """
    TCE-07 — AI component variant generation via cif.variant-generator prompt.

    Pure template-driven — no DB lookup. Caller supplies component_type,
    original_content, brand_context, and variant_count.
    """
    variables: dict[str, Any] = {
        "component_type": body.component_type,
        "original_content": json.dumps(body.original_content),
        "brand_context": body.brand_context,
        "variant_count": str(body.variant_count),
    }

    t0 = time.monotonic()
    try:
        raw = await call_external(
            prompt="",
            task_type="recommend",
            variables=variables,
            prompt_id="cif.variant-generator",
        )
    except Exception as e:
        logger.error("variant-generate: LLM call failed: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    latency_ms = int((time.monotonic() - t0) * 1000)

    variants = _parse_list_response(
        raw,
        list_key="variants",
        endpoint="/api/v1/copilot/variant-generate",
        prompt_id="cif.variant-generator",
        task_type="recommend",
    )

    return {
        "variants": variants,
        "raw_response": raw,
        "component_type": body.component_type,
        "variant_count": body.variant_count,
        "latency_ms": latency_ms,
    }


# ---------------------------------------------------------------------------
# TCE-08 — automated CHubs pipeline (brief → deployed slug)
# ---------------------------------------------------------------------------

# HCTS hard-block thresholds (defaults to 100 when the trait is absent from
# the caller's profile — a missing score does not fail the check).
_HCTS_MIN_TRUST = 60
_HCTS_MIN_ETHICS = 65
_HCTS_MIN_AUTHENTICITY = 55


class SurfaceCreateBrief(BaseModel):
    name: str
    description: Optional[str] = None
    scss_position: str = "entry"
    hcts_target_profile: Optional[dict] = None
    cqx_intensity: str = "medium"
    components: list[dict] = Field(default_factory=list)
    auto_launch: bool = False
    auto_launch_threshold: int = Field(default=80, ge=0, le=100)


class SurfaceCreateBatchBody(BaseModel):
    briefs: list[SurfaceCreateBrief]
    stop_on_failure: bool = False
    # Batch-level AUTO_LAUNCH defaults — applied uniformly to every brief,
    # overriding any per-brief settings so the cohort is gated consistently.
    auto_launch: bool = False
    auto_launch_threshold: int = Field(default=80, ge=0, le=100)


_RENDERER_BASE = "https://sd-chubs-renderer.vercel.app"


def _check_hcts(profile: Optional[dict]) -> tuple[bool, Optional[str]]:
    p = profile or {}
    trust = p.get("trust", 100)
    ethics = p.get("ethics", 100)
    authenticity = p.get("authenticity", 100)
    if trust < _HCTS_MIN_TRUST:
        return False, f"trust {trust} < {_HCTS_MIN_TRUST}"
    if ethics < _HCTS_MIN_ETHICS:
        return False, f"ethics {ethics} < {_HCTS_MIN_ETHICS}"
    if authenticity < _HCTS_MIN_AUTHENTICITY:
        return False, f"authenticity {authenticity} < {_HCTS_MIN_AUTHENTICITY}"
    return True, None


def _evaluate_auto_launch(
    hcts_profile: Optional[dict],
    conviction_expectation: str,
    threshold: int = 80,
) -> tuple[bool, str, Optional[float]]:
    """Decide whether a surface may deploy without human review.

    Returns (approved, reason, avg_hcts_score). avg_hcts_score is None when
    no scores were provided.
    """
    if conviction_expectation != "actionable":
        return False, "conviction_expectation not actionable", None

    profile = hcts_profile or {}
    scores = [v for v in profile.values() if isinstance(v, (int, float))]
    if not scores:
        return False, "no HCTS scores provided", None

    avg_score = sum(scores) / len(scores)
    if avg_score < threshold:
        return (
            False,
            f"avg HCTS score {avg_score:.1f} below threshold {threshold}",
            avg_score,
        )

    trust = profile.get("trust", 100)
    ethics = profile.get("ethics", 100)
    authenticity = profile.get("authenticity", 100)
    if trust < _HCTS_MIN_TRUST:
        return False, "HCTS hard block: trust < 60", avg_score
    if ethics < _HCTS_MIN_ETHICS:
        return False, "HCTS hard block: ethics < 65", avg_score
    if authenticity < _HCTS_MIN_AUTHENTICITY:
        return False, "HCTS hard block: authenticity < 55", avg_score

    return True, "AUTO_LAUNCH approved", avg_score


def _emit_auto_launch_signal(
    db: AsyncSession,
    surface_id: UUID,
    version_id: UUID,
    event_data: dict,
) -> None:
    """Best-effort SignalEvent emission — never raises."""
    try:
        db.add(SignalEvent(
            surface_id=surface_id,
            event_type=EventType.auto_launch,
            event_data={
                **event_data,
                "surface_version_id": str(version_id) if version_id else None,
            },
        ))
    except Exception as e:
        logger.warning("auto_launch signal emission failed: %s", e)


async def _run_surface_pipeline(
    db: AsyncSession,
    brief: SurfaceCreateBrief,
    api_key: str,
) -> dict:
    """Run one brief through CQX → HCTS → create → review → publish → deploy.

    Raises HTTPException on any stage failure — callers must translate to a
    status-coded response. Returns the success dict on completion.
    """
    start = time.monotonic()

    # 1. CQX sequencing
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

    # 2. HCTS hard blocks
    hcts_ok, hcts_reason = _check_hcts(brief.hcts_target_profile)
    if not hcts_ok:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "hcts_blocked",
                "failure_reason": hcts_reason,
            },
        )

    # 3. Create surface via service layer
    try:
        sections = [
            SectionIn(
                section_id="main",
                components=[ComponentConfigIn(**c) for c in seq.component_sequence],
            )
        ]
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

    # 4. State transitions draft → review → published
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

    # 5. AUTO_LAUNCH decision — only evaluated when the caller opts in
    auto_launch_block: Optional[dict] = None
    should_deploy = True
    if brief.auto_launch:
        approved, reason, avg_score = _evaluate_auto_launch(
            brief.hcts_target_profile,
            seq.conviction_expectation,
            brief.auto_launch_threshold,
        )
        if approved:
            auto_launch_block = {
                "approved": True,
                "reason": reason,
                "avg_hcts_score": round(avg_score, 2) if avg_score is not None else None,
                "threshold_used": brief.auto_launch_threshold,
                "deployed": True,
            }
        else:
            should_deploy = False
            # Mint a preview token so the surface can be reviewed by a human.
            secret = secrets.token_urlsafe(16)
            preview_id = f"prev-{secret[:8]}"
            expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
            token = PreviewToken(
                preview_id=preview_id,
                asset_id=surface.id,
                asset_type="conversion_surface",
                asset_slug=surface.slug,
                version_id=version.id,
                expires_at=expires_at,
                created_by=api_key,
            )
            db.add(token)
            preview_url = f"{_RENDERER_BASE}/?slug={surface.slug}&preview={preview_id}"
            auto_launch_block = {
                "approved": False,
                "reason": reason,
                "avg_hcts_score": round(avg_score, 2) if avg_score is not None else None,
                "threshold_used": brief.auto_launch_threshold,
                "deployed": False,
                "routed_to_review": True,
                "preview_id": preview_id,
                "preview_url": preview_url,
            }

        _emit_auto_launch_signal(
            db, surface.id, version.id,
            {
                "slug": surface.slug,
                "auto_launch_approved": approved,
                "avg_hcts_score": round(avg_score, 2) if avg_score is not None else None,
                "conviction_expectation": seq.conviction_expectation,
                "threshold_used": brief.auto_launch_threshold,
                **(
                    {"approval_reason": reason}
                    if approved
                    else {"block_reason": reason, "routed_to_review": True}
                ),
            },
        )

    # 6. Deploy to production (skipped when AUTO_LAUNCH blocks)
    deployment_id: Optional[str] = None
    if should_deploy:
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

    latency_ms = int((time.monotonic() - start) * 1000)
    response: dict = {
        "surface_id": str(surface.id),
        "version_id": str(version.id),
        "slug": surface.slug,
        "deployment_id": deployment_id,
        "cqx_sequencing": {
            "validation": seq.validation,
            "conviction_expectation": seq.conviction_expectation,
            "stage_coverage": seq.stage_coverage,
        },
        "hcts_check": "passed",
        "latency_ms": latency_ms,
    }
    if auto_launch_block is not None:
        response["auto_launch"] = auto_launch_block
    return response


@router.post("/surface-create")
async def surface_create(
    body: SurfaceCreateBrief,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """TCE-08 — single brief → deployed surface in one call."""
    try:
        return await _run_surface_pipeline(db, body, api_key)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("surface-create pipeline error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_pipeline_isolated(
    index: int,
    brief: SurfaceCreateBrief,
    api_key: str,
) -> dict:
    """Run one pipeline with an independent DB session (for gather)."""
    async with AsyncSessionLocal() as db:
        try:
            result = await _run_surface_pipeline(db, brief, api_key)
            await db.commit()
            out: dict = {
                "index": index,
                "status": "success",
                "slug": result["slug"],
                "surface_id": result["surface_id"],
                "version_id": result["version_id"],
                "deployment_id": result["deployment_id"],
                "conviction_expectation":
                    result["cqx_sequencing"]["conviction_expectation"],
            }
            if "auto_launch" in result:
                out["auto_launch"] = result["auto_launch"]
            return out
        except HTTPException as he:
            await db.rollback()
            detail = he.detail if isinstance(he.detail, dict) else {"error": str(he.detail)}
            return {
                "index": index,
                "status": "failed",
                "error": detail.get("failure_reason") or detail.get("error") or str(detail),
                "failure_mode": detail.get("failure_mode"),
            }
        except Exception as e:
            await db.rollback()
            logger.exception("batch pipeline index=%d error: %s", index, e)
            return {
                "index": index,
                "status": "failed",
                "error": str(e),
                "failure_mode": "unexpected_error",
            }


@router.post("/surface-create-batch")
async def surface_create_batch(
    body: SurfaceCreateBatchBody,
    api_key: str = Depends(require_api_key),
):
    """TCE-08 — array of briefs processed in parallel via asyncio.gather.

    When ``auto_launch`` is set at the batch level, the value and threshold
    are propagated onto every brief — per-brief auto_launch settings are
    overridden so the cohort is gated consistently.
    """
    start = time.monotonic()

    # Propagate batch-level AUTO_LAUNCH settings onto each brief.
    for brief in body.briefs:
        brief.auto_launch = body.auto_launch
        brief.auto_launch_threshold = body.auto_launch_threshold

    if body.stop_on_failure:
        # Sequential with early exit
        results: list[dict] = []
        for i, brief in enumerate(body.briefs):
            r = await _run_pipeline_isolated(i, brief, api_key)
            results.append(r)
            if r["status"] == "failed":
                break
    else:
        tasks = [
            _run_pipeline_isolated(i, brief, api_key)
            for i, brief in enumerate(body.briefs)
        ]
        results = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    latency_ms = int((time.monotonic() - start) * 1000)

    return {
        "results": list(results),
        "total": len(body.briefs),
        "succeeded": succeeded,
        "failed": failed,
        "latency_ms": latency_ms,
    }
