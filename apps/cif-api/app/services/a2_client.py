"""A2 Underwriting Service client — TCE-11 Path 3.

ROUTING: Public Railway URL (Option B — public-route mode).
TODO: Migrate to Railway internal hostname once private service-to-service
networking is confirmed (Option A). Swap the base URL in
``app/core/config.py`` when migrating; no logic change should be required.

SCOPE NOTE (Path 3): Only /v1/a2/underwrite is wired. /v1/hub/generate is
intentionally omitted — its request contract demands allocation_id,
translation_id, campaign_id, pilot_id etc., none of which are produced
elsewhere in CIF today. Fabricating them would be incorrect. A future
path (Path 1/2) will wire hub/generate once an upstream campaign object
model is available.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

_A2_TIMEOUT = settings.A2_TIMEOUT_SECONDS

_NINE_PD: tuple[str, ...] = (
    "presence", "trust", "authenticity", "momentum", "taste",
    "empathy", "autonomy", "resonance", "ethics",
)


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if settings.A2_API_KEY:
        h["Authorization"] = f"Bearer {settings.A2_API_KEY}"
        h["X-API-Key"] = settings.A2_API_KEY
    return h


def _build_test_underwrite_payload(brand_id: str, hcts_profile: dict) -> dict:
    """TEST MODE: synthetic A2 underwrite payload derived from a CIF HCTS profile.

    Inputs are CIF-style (0–100); outputs are A2-style (0–1).
    Missing 9PD traits default to 70 (neutral → 0.7 after scaling).
    stage_profiles are identical across all 3 stages (image/video/landing_page)
    — CIF has no per-stage differentiation today.

    SYNTHETIC INPUT — not derived from real campaign scoring data.
    TODO (Path 2): Replace with real per-stage profiles from ``~/base/`` A2
    system once the campaign object model is exposed.
    """
    hcts_profile = hcts_profile or {}

    profile_01: dict[str, float] = {}
    for trait in _NINE_PD:
        raw = hcts_profile.get(
            trait,
            hcts_profile.get(trait.capitalize(), 70),
        )
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = 70.0
        profile_01[trait] = round(min(1.0, max(0.0, val / 100.0)), 3)

    avg = sum(profile_01.values()) / len(profile_01)
    trust_01 = profile_01["trust"]
    ethics_01 = profile_01["ethics"]
    gate_ok = trust_01 >= 0.60 and ethics_01 >= 0.65

    return {
        "brand_id": brand_id,
        "sector": "BEAUTY_SKINCARE",
        "stage_profiles": {
            "image": profile_01,
            "video": profile_01,
            "landing_page": profile_01,
        },
        "stage_fits": {
            "image":        round(avg * 0.9, 3),
            "video":        round(avg * 0.85, 3),
            "landing_page": round(avg, 3),
        },
        "stage_confidences": {
            "image":        round(min(1.0, avg + 0.05), 3),
            "video":        round(min(1.0, avg + 0.03), 3),
            "landing_page": round(min(1.0, avg + 0.08), 3),
        },
        "stage_gates_passed": {
            "image":        gate_ok,
            "video":        gate_ok,
            "landing_page": gate_ok,
        },
        "measurement_quality": 0.85,
    }


async def a2_underwrite(brand_id: str, hcts_profile: dict) -> dict[str, Any]:
    """POST /v1/a2/underwrite — synthetic payload derived from CIF HCTS.

    Returns the A2 response dict augmented with ``_latency_ms`` and
    ``_payload_sent`` (the synthetic body, for audit) keys.
    """
    payload = _build_test_underwrite_payload(brand_id, hcts_profile)

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=_A2_TIMEOUT) as client:
            r = await client.post(
                f"{settings.A2_SERVICE_URL}/v1/a2/underwrite",
                json=payload,
                headers=_headers(),
            )
            r.raise_for_status()
            latency_ms = int((time.time() - start) * 1000)
            body = r.json()
            logger.info(
                "a2_underwrite_success latency_ms=%d decision=%s brand_id=%s",
                latency_ms, body.get("decision"), brand_id,
            )
            return {**body, "_latency_ms": latency_ms, "_payload_sent": payload}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        logger.error(
            "a2_underwrite_error latency_ms=%d brand_id=%s error=%s",
            latency_ms, brand_id, str(e),
        )
        raise
