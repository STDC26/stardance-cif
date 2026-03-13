"""
CIF AI API — Phase-6 Track 1

Exposes AI provider health checks and inference endpoints.
All inference flows through the router — never direct to clients.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_api_key
from app.services.ai_provider import generate, AITaskType
from app.services.ai_provider.routing_policy import AIProvider
from app.services.ai_provider.local_llm_client import check_local_health
from app.services.ai_provider.external_llm_client import check_remote_health

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class InferenceRequest(BaseModel):
    task_type: AITaskType
    prompt: str
    context: Optional[dict[str, Any]] = None
    system: Optional[str] = None
    force_provider: Optional[AIProvider] = None


@router.get("/health")
async def ai_health(_: str = Depends(require_api_key)):
    """Returns health status of both local and remote providers."""
    local = await check_local_health()
    remote = await check_remote_health()
    overall = (
        "ok"
        if local.get("status") == "ok" or remote.get("status") == "ok"
        else "degraded"
    )
    return {"status": overall, "local": local, "remote": remote}


@router.post("/generate")
async def ai_generate(
    body: InferenceRequest,
    _: str = Depends(require_api_key),
):
    """
    Primary inference endpoint.
    Routes through ai_provider router based on task_type.
    Returns provider, model, response, latency_ms.
    """
    result = await generate(
        task_type=body.task_type,
        prompt=body.prompt,
        context=body.context,
        system=body.system,
        force_provider=body.force_provider,
    )
    if result.get("error") and not result.get("response"):
        raise HTTPException(
            status_code=503,
            detail=f"AI inference failed: {result['error']}",
        )
    return result


@router.post("/summarize")
async def summarize(
    body: dict,
    _: str = Depends(require_api_key),
):
    """Convenience: signal or experiment summarization via local model."""
    text = body.get("text", "")
    task = body.get("task_type", "signal_summary")
    if not text:
        raise HTTPException(status_code=422, detail="text field required")
    try:
        task_type = AITaskType(task)
    except ValueError:
        task_type = AITaskType.SIGNAL_SUMMARY
    result = await generate(
        task_type=task_type,
        prompt=f"Summarize the following concisely:\n\n{text}",
        system="You are a precise summarization assistant for a "
               "marketing intelligence platform. Return only the summary.",
    )
    return {
        "summary": result["response"],
        "provider": result["provider"],
        "model": result["model"],
        "latency_ms": result["latency_ms"],
    }


@router.post("/experiment-summary")
async def experiment_summary(
    body: dict,
    _: str = Depends(require_api_key),
):
    """
    Generate AI summary of experiment result.
    Accepts context dict for Retrieval Layer grounding (Sprint 3).
    """
    context = body.get("context", {})
    prompt = body.get("prompt", "Summarize this experiment.")
    result = await generate(
        task_type=AITaskType.EXPERIMENT_SUMMARY,
        prompt=prompt,
        context=context,
        system="You are a concise experiment analyst. "
               "Summarize results, identify the winning variant, "
               "and state one clear optimization recommendation.",
    )
    return {
        "summary": result["response"],
        "provider": result["provider"],
        "model": result["model"],
        "latency_ms": result["latency_ms"],
    }
