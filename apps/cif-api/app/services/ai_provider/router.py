"""
CIF AI Router — Phase-6 Track 1

Primary entry point for all CIF AI inference calls.

Public interface:
    result = await generate(
        task_type=AITaskType.EXPERIMENT_SUMMARY,
        prompt="...",
        context={"experiment_id": "abc", "variant_count": 2},
    )

Response schema:
    {
        "provider": "local",
        "model": "qwen2.5:7b-instruct",
        "response": "...",
        "latency_ms": 1230,
        "task_type": "experiment_summary",
        "fallback_used": false,
        "error": null
    }

Routing is deterministic by task_type via routing_policy.
Local failures fall back to remote with warning logged.
Remote tasks do not fall back to local.
"""

import logging
import time
from typing import Any, Optional

from app.services.ai_provider.routing_policy import (
    AIProvider,
    AITaskType,
    ANTHROPIC_MODEL,
    OLLAMA_MODEL,
    resolve_provider,
)
from app.services.ai_provider.local_llm_client import call_local
from app.services.ai_provider.external_llm_client import call_external

logger = logging.getLogger(__name__)


def _build_context_block(context: Optional[dict[str, Any]]) -> str:
    """Converts context dict into a formatted string for prompt injection."""
    if not context:
        return ""
    lines = ["[Context]"]
    for k, v in context.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines) + "\n\n"


async def generate(
    task_type: AITaskType,
    prompt: str,
    context: Optional[dict[str, Any]] = None,
    system: Optional[str] = None,
    force_provider: Optional[AIProvider] = None,
) -> dict[str, Any]:
    """
    Routes an inference request to the appropriate provider.

    Args:
        task_type:      Canonical CIF task type from AITaskType enum.
        prompt:         User/operator prompt string.
        context:        Optional retrieval context dict — enables Sprint 3
                        Retrieval Layer grounding.
        system:         Optional system instruction override.
        force_provider: Override routing policy. Use sparingly.

    Returns:
        dict with keys: provider, model, response, latency_ms,
                        task_type, fallback_used, error
    """
    context_block = _build_context_block(context)
    full_prompt = f"{context_block}{prompt}" if context_block else prompt

    intended = force_provider if force_provider else resolve_provider(task_type)

    start = time.monotonic()

    if intended == AIProvider.LOCAL:
        try:
            response = await call_local(full_prompt, system)
            latency_ms = int((time.monotonic() - start) * 1000)
            return {
                "provider": AIProvider.LOCAL.value,
                "model": OLLAMA_MODEL,
                "response": response,
                "latency_ms": latency_ms,
                "task_type": task_type.value,
                "fallback_used": False,
                "error": None,
            }
        except Exception as e:
            logger.warning(
                "router: local call failed task=%s error=%s — "
                "falling back to remote",
                task_type.value, str(e),
            )
            try:
                response = await call_external(full_prompt, system)
                latency_ms = int((time.monotonic() - start) * 1000)
                return {
                    "provider": AIProvider.REMOTE.value,
                    "model": ANTHROPIC_MODEL,
                    "response": response,
                    "latency_ms": latency_ms,
                    "task_type": task_type.value,
                    "fallback_used": True,
                    "error": str(e),
                }
            except Exception as e2:
                latency_ms = int((time.monotonic() - start) * 1000)
                logger.error(
                    "router: remote fallback also failed task=%s error=%s",
                    task_type.value, str(e2),
                )
                return {
                    "provider": AIProvider.REMOTE.value,
                    "model": ANTHROPIC_MODEL,
                    "response": "",
                    "latency_ms": latency_ms,
                    "task_type": task_type.value,
                    "fallback_used": True,
                    "error": str(e2),
                }

    else:
        try:
            response = await call_external(full_prompt, system)
            latency_ms = int((time.monotonic() - start) * 1000)
            return {
                "provider": AIProvider.REMOTE.value,
                "model": ANTHROPIC_MODEL,
                "response": response,
                "latency_ms": latency_ms,
                "task_type": task_type.value,
                "fallback_used": False,
                "error": None,
            }
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "router: remote call failed task=%s error=%s",
                task_type.value, str(e),
            )
            return {
                "provider": AIProvider.REMOTE.value,
                "model": ANTHROPIC_MODEL,
                "response": "",
                "latency_ms": latency_ms,
                "task_type": task_type.value,
                "fallback_used": False,
                "error": str(e),
            }
