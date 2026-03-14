"""
CIF QDS Draft Generator — Phase-6 Sprint-5

Generates AI-assisted QDS diagnostic flow drafts.
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

QDS_DRAFT_SYSTEM_PROMPT = """You are a creative intelligence assistant
that generates QDS (Quick Diagnostic Sequence) flow drafts. Given context
about an existing QDS or a brief, generate a new diagnostic flow draft
as structured JSON.

Return ONLY valid JSON with these keys:
- name: string (descriptive flow name)
- slug: string (kebab-case, URL-safe)
- description: string (purpose of the diagnostic flow)
- steps: array of objects, each with:
  - step_number: integer
  - title: string
  - question: string
  - options: array of strings
- outcomes: array of objects, each with:
  - label: string
  - description: string
  - condition: string (which step/option leads here)

Do not include any text outside the JSON object."""


def _parse_json_response(text: str) -> dict:
    """Extracts JSON from LLM response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


async def generate_qds_draft(
    db: AsyncSession,
    slug: Optional[str] = None,
    qds_asset_id: Optional[UUID] = None,
    brief: Optional[str] = None,
) -> dict:
    """
    Generates an AI-assisted QDS diagnostic flow draft.

    Args:
        db:             AsyncSession
        slug:           Optional slug of existing QDS for context
        qds_asset_id:   Optional QDS asset UUID for context
        brief:          Optional freeform brief describing desired flow

    Returns:
        dict with keys: draft, status, provider, latency_ms,
                        context_keys, error
    """
    try:
        context = {}
        if slug or qds_asset_id:
            context = await build_context(
                request=RetrievalRequest(
                    qds_asset_id=qds_asset_id,
                    slug=slug,
                    include_signals=True,
                    include_experiment=False,
                    include_qds=True,
                ),
                db=db,
            )

        prompt = "Generate a new QDS diagnostic flow draft.\n"
        if brief:
            prompt += f"Brief: {brief}\n"
        if context:
            prompt += (
                f"Reference QDS: {context.get('qds_name', 'Unknown')}\n"
                f"Step count: {context.get('qds_step_count', 0)}\n"
                f"Completion rate: "
                f"{context.get('qds_completion_rate', '0%')}\n"
                f"Total sessions: "
                f"{context.get('qds_total_sessions', 0)}\n"
                f"Completed sessions: "
                f"{context.get('qds_completed_sessions', 0)}\n"
                f"Total signal events: "
                f"{context.get('signal_total_events', 0)}\n"
            )

        result = await generate(
            task_type=AITaskType.ASSET_DRAFT,
            prompt=prompt,
            context=context,
            system=QDS_DRAFT_SYSTEM_PROMPT,
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
        logger.error("qds_draft_generator error: %s", str(e))
        return {"error": str(e)}
