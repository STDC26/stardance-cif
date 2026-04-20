"""A2 Underwriting Service client — TCE-11.

ROUTING: Currently using public Railway URL (Option B — public-route mode).
TODO: Migrate to Railway internal hostname once private service-to-service
networking is confirmed (Option A). Reference ticket: TCE-11 Option A
follow-up. Swap the base URL in ``app/core/config.py`` when migrating; no
logic change should be required here.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

_A2_TIMEOUT = settings.A2_TIMEOUT_SECONDS


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if settings.A2_API_KEY:
        # A2 accepts either an Authorization bearer or an X-API-Key header.
        # Sending both is safe — receivers read the one they expect.
        h["Authorization"] = f"Bearer {settings.A2_API_KEY}"
        h["X-API-Key"] = settings.A2_API_KEY
    return h


async def a2_underwrite(brand_context: dict[str, Any]) -> dict[str, Any]:
    """POST /v1/a2/underwrite.

    Returns a dict carrying ``decision``, ``calibration_event_id``,
    ``confidence``, ``system_fit``, plus an ``_latency_ms`` field.
    """
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=_A2_TIMEOUT) as client:
            r = await client.post(
                f"{settings.A2_SERVICE_URL}/v1/a2/underwrite",
                json=brand_context,
                headers=_headers(),
            )
            r.raise_for_status()
            latency_ms = int((time.time() - start) * 1000)
            body = r.json()
            logger.info(
                "a2_underwrite_success latency_ms=%d decision=%s",
                latency_ms, body.get("decision"),
            )
            return {**body, "_latency_ms": latency_ms}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        logger.error(
            "a2_underwrite_error latency_ms=%d error=%s",
            latency_ms, str(e),
        )
        raise


async def a2_hub_generate(
    calibration_event_id: str,
    brand_context: dict[str, Any],
) -> dict[str, Any]:
    """POST /v1/hub/generate.

    Returns ``hub_id``, ``routing_band`` (correct source for the X-PLA-Band
    CAST header), ``gate_pass``, ``tis``, ``gci``, ``clg``, ``status``, plus
    ``_latency_ms``.
    """
    start = time.time()
    try:
        payload = {"calibration_event_id": calibration_event_id, **brand_context}
        async with httpx.AsyncClient(timeout=_A2_TIMEOUT) as client:
            r = await client.post(
                f"{settings.A2_SERVICE_URL}/v1/hub/generate",
                json=payload,
                headers=_headers(),
            )
            r.raise_for_status()
            latency_ms = int((time.time() - start) * 1000)
            body = r.json()
            logger.info(
                "a2_hub_generate_success latency_ms=%d gate_pass=%s routing_band=%s",
                latency_ms, body.get("gate_pass"), body.get("routing_band"),
            )
            return {**body, "_latency_ms": latency_ms}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        logger.error(
            "a2_hub_generate_error latency_ms=%d error=%s",
            latency_ms, str(e),
        )
        raise
