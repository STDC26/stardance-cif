"""
CIF Local LLM Client — Phase-6 Track 1

httpx client for Ollama /api/generate.
Pattern adapted from SCOUT llm_adapter.py.
CIF-native — does not import SCOUT code.
Ollama runs on loopback at http://127.0.0.1:11434 on SD-Factory.
"""

import logging
from typing import Optional

import httpx

from app.services.ai_provider.routing_policy import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)

logger = logging.getLogger(__name__)


async def call_local(
    prompt: str,
    system: Optional[str] = None,
) -> str:
    """
    Sends prompt to Ollama /api/generate.
    Prepends system prompt if provided.
    Raises httpx.HTTPError on failure.
    """
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("response", "").strip()
        logger.debug(
            "local_llm_client: model=%s prompt_len=%d response_len=%d",
            OLLAMA_MODEL, len(full_prompt), len(result),
        )
        return result


async def check_local_health() -> dict:
    """Returns Ollama health status and approved model availability."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            approved = OLLAMA_MODEL in models
            return {
                "status": "ok" if approved else "model_missing",
                "endpoint": OLLAMA_BASE_URL,
                "approved_model": OLLAMA_MODEL,
                "approved_model_present": approved,
                "installed_models": models,
            }
    except Exception as e:
        return {
            "status": "unreachable",
            "endpoint": OLLAMA_BASE_URL,
            "error": str(e),
        }
