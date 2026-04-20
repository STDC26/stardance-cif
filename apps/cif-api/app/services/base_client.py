"""BASE Measurement Service client — TCE-15.

Calls the BASE asset upload and trait-scoring endpoints to produce real
NinePDProfile measurements for A2 underwriting input. Replaces the
synthetic payload path from TCE-11 Path 3.

Service:      https://base-production-c0e3.up.railway.app
Auth:         X-API-Key header, OPTIONAL. BASE defaults to
              ``BASE_API_KEY_REQUIRED=false``. Only send the header when
              ``settings.BASE_API_KEY`` is configured.
Scale:        BASE ``nine_pd_profile`` / ``hct_profile`` is 0.0–1.0 floats
              — matches A2's NinePDProfile Pydantic constraint exactly.
              No scaling needed on the FORGE side.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

BASE_URL = settings.BASE_SERVICE_URL
BASE_POLL_INTERVAL = 3.0     # seconds between polls while analysis runs
BASE_POLL_TIMEOUT = 120.0    # max seconds to wait for analysis to complete

_NINE_TRAITS = (
    "presence", "trust", "authenticity", "momentum", "taste",
    "empathy", "autonomy", "resonance", "ethics",
)


def _headers(api_key: Optional[str]) -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    effective = api_key if api_key is not None else settings.BASE_API_KEY
    if effective:
        h["X-API-Key"] = effective
    return h


async def upload_stage_asset(
    file_bytes: bytes,
    asset_type: str,         # "image" | "video" | "pdf" | "document"
    session_id: str,
    brand_context: dict,
    api_key: Optional[str] = None,
) -> str:
    """Upload one stage asset to BASE. Returns ``asset_id`` from the 202."""
    start = time.time()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BASE_URL}/api/v1/assets/upload",
            headers=_headers(api_key),
            data={
                "asset_type": asset_type,
                "session_id": session_id,
                "brand_context": json.dumps(brand_context),
            },
            files={"file": ("asset", file_bytes, "application/octet-stream")},
        )
        r.raise_for_status()
        data = r.json()
        asset_id = data["asset_id"]
        latency = int((time.time() - start) * 1000)
        logger.info(
            "base_upload_success asset_id=%s asset_type=%s latency_ms=%d",
            asset_id, asset_type, latency,
        )
        return asset_id


async def poll_traits(
    asset_id: str,
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """Poll BASE until trait analysis is complete. Returns the traits body."""
    deadline = time.time() + BASE_POLL_TIMEOUT
    attempts = 0

    async with httpx.AsyncClient(timeout=15.0) as client:
        while time.time() < deadline:
            attempts += 1
            r = await client.get(
                f"{BASE_URL}/api/v1/assets/{asset_id}/traits",
                headers=_headers(api_key),
            )
            r.raise_for_status()
            data = r.json()

            # Completion heuristics — BASE's traits endpoint may return
            # either a status string or a populated trait_scores list when
            # the background task has finished writing rows to
            # base_trait_scores. Check both.
            status = data.get("status") or data.get("score_status", "")
            trait_scores = data.get("trait_scores") or data.get("traits", [])
            if status in ("analyzed", "complete") or (
                isinstance(trait_scores, list) and len(trait_scores) >= 9
            ):
                logger.info(
                    "base_traits_ready asset_id=%s attempts=%d",
                    asset_id, attempts,
                )
                return data

            logger.debug(
                "base_traits_pending asset_id=%s status=%s attempt=%d",
                asset_id, status, attempts,
            )
            await asyncio.sleep(BASE_POLL_INTERVAL)

    raise TimeoutError(
        f"BASE analysis timed out after {BASE_POLL_TIMEOUT}s "
        f"for asset {asset_id}"
    )


def extract_nine_pd_profile(traits_response: dict) -> dict[str, float]:
    """Produce a 9-trait float dict (0.0–1.0) from a BASE traits response.

    Priority order:
      1. ``nine_pd_profile`` / ``hct_profile`` — native 0.0–1.0 float dicts.
      2. ``trait_scores`` / ``traits`` list — rows from base_trait_scores.

    Uses a 0.7 fallback for any missing trait so the shape is always
    complete and passes A2's Pydantic validation.

    Does NOT read ``dimension_allocation`` (0–100 sum-to-100 — different
    semantic) or ``HCTSEvaluateResponse.traits`` (0–100 ints — wrong scale).
    """
    # Priority 1: native profile dict, already 0.0–1.0
    for key in ("nine_pd_profile", "hct_profile"):
        profile = traits_response.get(key)
        if isinstance(profile, dict) and profile:
            return {t: float(profile.get(t, 0.7)) for t in _NINE_TRAITS}

    # Priority 2: trait_scores rows
    trait_list = traits_response.get("trait_scores") or traits_response.get("traits") or []
    if isinstance(trait_list, list) and trait_list:
        # Row shapes observed: {"trait_name", "trait_score"} or {"name", "score"}
        by_trait: dict[str, float] = {}
        for row in trait_list:
            if not isinstance(row, dict):
                continue
            name = row.get("trait_name") or row.get("name")
            score = row.get("trait_score") if "trait_score" in row else row.get("score")
            if name and score is not None:
                try:
                    by_trait[name] = float(score)
                except (TypeError, ValueError):
                    continue
        if by_trait:
            return {t: by_trait.get(t, 0.7) for t in _NINE_TRAITS}

    raise ValueError(
        f"No valid NinePDProfile in BASE response. keys={list(traits_response.keys())}"
    )


def extract_confidence(traits_response: dict) -> float:
    """Pull overall confidence from a BASE traits response (0.0–1.0)."""
    confidence = traits_response.get("confidence")
    if isinstance(confidence, dict):
        overall = confidence.get("overall", 0.85)
        try:
            return float(overall)
        except (TypeError, ValueError):
            return 0.85
    if isinstance(confidence, (int, float)):
        return float(confidence)
    # Fallback: derive from per-row confidence values when the endpoint
    # returns trait_scores rows with their own confidence field.
    trait_list = traits_response.get("trait_scores") or traits_response.get("traits") or []
    if isinstance(trait_list, list) and trait_list:
        vals = [
            float(r.get("confidence"))
            for r in trait_list
            if isinstance(r, dict) and r.get("confidence") is not None
        ]
        if vals:
            return round(sum(vals) / len(vals), 4)
    return 0.85
