"""Stage profiler — TCE-15.

Builds the 4-field A2 underwrite input bundle from three BASE measurements:

    { stage_profiles, stage_fits, stage_confidences,
      stage_gates_passed, measurement_quality }

The three BASE measurements run in parallel; their ``nine_pd_profile``
outputs flow through A2 without scale transformation (both are 0.0–1.0).

INTERIM_DERIVATIONS — TCE-15
    ``stage_fits``, ``stage_gates_passed``, and ``measurement_quality`` are
    derived in this file from the NinePDProfile using locked formulas
    pending migration to Stardance Measurement Core (TCE-20). These
    formulas are NOT canonical measurement logic.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional

from app.services.base_client import (
    extract_confidence,
    extract_nine_pd_profile,
    poll_traits,
    upload_stage_asset,
)


logger = logging.getLogger(__name__)


def _compute_stage_fit(profile: dict[str, float]) -> float:
    """INTERIM_DERIVATION (TCE-15). Weighted average of key conversion traits.

    Formula: ``trust * 0.4 + authenticity * 0.3 + resonance * 0.3``
    Migrate to Stardance Measurement Core (TCE-20).
    """
    return (
        profile.get("trust", 0.7) * 0.4
        + profile.get("authenticity", 0.7) * 0.3
        + profile.get("resonance", 0.7) * 0.3
    )


def _compute_stage_gate(profile: dict[str, float]) -> bool:
    """INTERIM_DERIVATION (TCE-15). Hard conversion gate per stage.

    Formula: ``trust >= 0.60 AND ethics >= 0.65 AND authenticity >= 0.55``
    Migrate to Stardance Measurement Core (TCE-20).
    """
    return (
        profile.get("trust", 0.0) >= 0.60
        and profile.get("ethics", 0.0) >= 0.65
        and profile.get("authenticity", 0.0) >= 0.55
    )


async def build_stage_profiles(
    image_bytes: bytes,
    video_bytes: bytes,
    landing_page_bytes: bytes,
    brand_context: dict[str, Any],
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """Upload 3 stage assets, poll for traits, assemble A2 input bundle.

    All three uploads share a single ``session_id`` so BASE's session sweep
    can compute cross-asset similarity if queried later.
    """
    session_id = str(uuid.uuid4())
    logger.info("stage_profiler_start session_id=%s", session_id)

    # 1. Upload all three stage assets in parallel
    image_id, video_id, lp_id = await asyncio.gather(
        upload_stage_asset(image_bytes, "image", session_id, brand_context, api_key),
        upload_stage_asset(video_bytes, "video", session_id, brand_context, api_key),
        upload_stage_asset(landing_page_bytes, "document", session_id, brand_context, api_key),
    )
    logger.info(
        "stage_profiler_uploaded image=%s video=%s landing_page=%s",
        image_id, video_id, lp_id,
    )

    # 2. Poll BASE until all three analyses complete
    image_traits, video_traits, lp_traits = await asyncio.gather(
        poll_traits(image_id, api_key),
        poll_traits(video_id, api_key),
        poll_traits(lp_id, api_key),
    )

    # 3. Extract NinePDProfiles (passthrough 0.0–1.0; no scaling)
    image_profile = extract_nine_pd_profile(image_traits)
    video_profile = extract_nine_pd_profile(video_traits)
    lp_profile = extract_nine_pd_profile(lp_traits)

    image_conf = extract_confidence(image_traits)
    video_conf = extract_confidence(video_traits)
    lp_conf = extract_confidence(lp_traits)

    stage_profiles = {
        "image": image_profile,
        "video": video_profile,
        "landing_page": lp_profile,
    }
    stage_confidences = {
        "image": image_conf,
        "video": video_conf,
        "landing_page": lp_conf,
    }
    stage_fits = {
        "image":        round(_compute_stage_fit(image_profile), 4),
        "video":        round(_compute_stage_fit(video_profile), 4),
        "landing_page": round(_compute_stage_fit(lp_profile), 4),
    }
    stage_gates_passed = {
        "image":        _compute_stage_gate(image_profile),
        "video":        _compute_stage_gate(video_profile),
        "landing_page": _compute_stage_gate(lp_profile),
    }

    # INTERIM_DERIVATION (TCE-15). Mean of stage confidences, clamped.
    measurement_quality = round(
        max(0.0, min(1.0, sum(stage_confidences.values()) / 3.0)),
        4,
    )

    lineage = {
        "session_id": session_id,
        "asset_ids": {
            "image": image_id,
            "video": video_id,
            "landing_page": lp_id,
        },
    }

    logger.info(
        "stage_profiler_complete session_id=%s measurement_quality=%.3f",
        session_id, measurement_quality,
    )

    return {
        "stage_profiles": stage_profiles,
        "stage_confidences": stage_confidences,
        "stage_fits": stage_fits,
        "stage_gates_passed": stage_gates_passed,
        "measurement_quality": measurement_quality,
        "_lineage": lineage,
    }
