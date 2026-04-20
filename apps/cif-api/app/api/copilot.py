"""
CIF Copilot API — Phase-6 Sprint-5

Exposes AI-assisted draft generation endpoints.
All endpoints return drafts with status="draft".
No platform state changes — drafts are returned, not persisted.
"""

import json
import logging
import re
import time
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.db.session import get_db
from app.services.ai_provider.external_llm_client import call_external
from app.services.copilot import (
    generate_draft,
    CopilotRequest,
    CopilotAction,
)
from app.services.retrieval import RetrievalRequest, build_context

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
