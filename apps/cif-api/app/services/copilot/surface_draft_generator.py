"""
CIF Surface Draft Generator — Phase-6 Sprint-5

Generates AI-assisted surface drafts using retrieval context.
Returns structured JSON drafts with status="draft" enforced.
"""

import json
import logging
import re
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import build_context, RetrievalRequest
from app.services.ai_provider import generate, AITaskType

logger = logging.getLogger(__name__)

SURFACE_DRAFT_SYSTEM_PROMPT = """You are a creative intelligence assistant
that generates surface drafts. Given context about an existing asset,
generate a new surface draft as structured JSON.

Return ONLY valid JSON with these keys:
- name: string (descriptive surface name)
- slug: string (kebab-case, URL-safe)
- type: string (one of: banner, modal, tooltip, card, embed)
- content: object with title, body, and cta_text keys
- targeting: object with audience and conditions keys

Do not include any text outside the JSON object."""


def _parse_json_response(text: str) -> dict:
    """Extracts JSON from LLM response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


async def generate_surface_draft(
    db: AsyncSession,
    slug: Optional[str] = None,
    asset_id: Optional[UUID] = None,
    brief: Optional[str] = None,
) -> dict:
    """
    Generates an AI-assisted surface draft.

    Args:
        db:         AsyncSession
        slug:       Optional slug of existing asset for context
        asset_id:   Optional asset UUID for context
        brief:      Optional freeform brief describing desired surface

    Returns:
        dict with keys: draft, status, provider, latency_ms,
                        context_keys, error
    """
    try:
        context = {}
        if slug or asset_id:
            context = await build_context(
                request=RetrievalRequest(
                    asset_id=asset_id,
                    slug=slug,
                    include_signals=True,
                    include_experiment=True,
                ),
                db=db,
            )

        prompt = "Generate a new surface draft.\n"
        if brief:
            prompt += f"Brief: {brief}\n"
        if context:
            prompt += (
                f"Reference asset: {context.get('asset_name', 'Unknown')}\n"
                f"Asset type: {context.get('asset_type', 'Unknown')}\n"
                f"Asset status: {context.get('asset_status', 'Unknown')}\n"
                f"Total events: "
                f"{context.get('signal_total_events', 0)}\n"
            )

            # Add QDS context if present
            if context.get('qds_name'):
                prompt += (
                    f"QDS name: {context.get('qds_name', '')}\n"
                    f"QDS step count: "
                    f"{context.get('qds_step_count', 0)}\n"
                    f"QDS completion rate: "
                    f"{context.get('qds_completion_rate', '0%')}\n"
                )

        result = await generate(
            task_type=AITaskType.ASSET_DRAFT,
            prompt=prompt,
            context=context,
            system=SURFACE_DRAFT_SYSTEM_PROMPT,
        )

        try:
            draft = _parse_json_response(result["response"])
        except (json.JSONDecodeError, ValueError):
            draft = {"raw_response": result["response"]}

        # Governance: enforce draft status
        draft["status"] = "draft"

        return {
            "draft": draft,
            "status": "draft",
            "provider": result["provider"],
            "latency_ms": result["latency_ms"],
            "context_keys": len(context),
        }

    except Exception as e:
        logger.error("surface_draft_generator error: %s", str(e))
        return {"error": str(e)}
