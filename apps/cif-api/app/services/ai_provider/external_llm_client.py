"""
CIF External LLM Client — Phase-6 Track 1 — updated T4-S1

Routes all remote LLM calls through stardance-llm-service.
No direct Anthropic API calls. Platform rule enforced.
"""

import logging
from typing import Any, Optional

import httpx

from app.services.ai_provider.routing_policy import (
    STARDANCE_LLM_SERVICE_URL,
    CIF_TO_LLM_TASK_MAP,
    PROMPT_ID_MAP,
    ANTHROPIC_TIMEOUT,
)

logger = logging.getLogger(__name__)


async def call_external(
    prompt: str,
    system: Optional[str] = None,
    task_type: str = "advanced_reasoning",
    variables: Optional[dict[str, Any]] = None,
) -> str:
    """
    Routes prompt through stardance-llm-service.
    No direct Anthropic calls — platform rule enforced.
    Raises httpx.HTTPError on service failure.

    When ``variables`` is provided, its keys are sent as the inner payload
    so that sd-llm-service's prompt template (resolved by ``prompt_id``)
    can substitute them via ``content.format(**payload)``. Without
    ``variables``, the rendered prompt is sent as ``{"prompt": ...}``
    (falls back to raw-template append on the remote side).
    """
    llm_task_type = CIF_TO_LLM_TASK_MAP.get(task_type, "specification_generation")
    prompt_id = PROMPT_ID_MAP.get(task_type, "cif.copilot")

    if variables:
        inner_payload: dict[str, Any] = dict(variables)
    else:
        inner_payload = {"prompt": prompt, "max_tokens": 1024}

    payload: dict[str, Any] = {
        "calling_system": "CIF",
        "task_type": llm_task_type,
        "prompt_id": prompt_id,
        "payload": inner_payload,
        "high_stakes_flag": False,
        "cache_eligible": True,
        "cache_ttl_seconds": 86400,
    }

    async with httpx.AsyncClient(timeout=ANTHROPIC_TIMEOUT) as client:
        resp = await client.post(
            f"{STARDANCE_LLM_SERVICE_URL}/v1/llm/call",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("content", "")
        logger.debug(
            "external_llm_client: routed via llm-service task=%s response_len=%d",
            llm_task_type, len(result),
        )
        return result


async def check_remote_health() -> dict:
    """Verifies stardance-llm-service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{STARDANCE_LLM_SERVICE_URL}/v1/llm/health")
        return {
            "status": "ok" if resp.status_code == 200 else "error",
            "http_code": resp.status_code,
            "routed_via": "stardance-llm-service",
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
            "routed_via": "stardance-llm-service",
        }
