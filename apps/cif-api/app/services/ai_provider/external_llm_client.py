"""
CIF External LLM Client — Phase-6 Track 1

httpx client for Anthropic Messages API.
Direct httpx — no anthropic SDK dependency.
"""

import logging
from typing import Any, Optional

import httpx

from app.services.ai_provider.routing_policy import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    ANTHROPIC_TIMEOUT,
)

logger = logging.getLogger(__name__)


async def call_external(
    prompt: str,
    system: Optional[str] = None,
) -> str:
    """
    Sends prompt to Anthropic /v1/messages.
    Raises ValueError if API key not set.
    Raises httpx.HTTPError on API failure.
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")

    payload: dict[str, Any] = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=ANTHROPIC_TIMEOUT) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["content"][0]["text"].strip()
        logger.debug(
            "external_llm_client: model=%s prompt_len=%d response_len=%d",
            ANTHROPIC_MODEL, len(prompt), len(result),
        )
        return result


async def check_remote_health() -> dict:
    """Verifies Anthropic API key is present and endpoint is reachable."""
    if not ANTHROPIC_API_KEY:
        return {"status": "no_api_key", "model": ANTHROPIC_MODEL}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
            )
        return {
            "status": "ok" if resp.status_code == 200 else "error",
            "http_code": resp.status_code,
            "model": ANTHROPIC_MODEL,
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
            "model": ANTHROPIC_MODEL,
        }
