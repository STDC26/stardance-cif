"""
CIF Copilot Package — Phase-6 Sprint-5

Provides AI-assisted draft generation and experiment recommendations.
All copilot services use the Retrieval Layer for context grounding
and the AI Router for inference.

Governance: LLMs generate drafts only. CIF Core controls all
lifecycle actions. All drafts are returned with status="draft".

Public interface:
    from app.services.copilot import generate_draft
    from app.services.copilot.copilot_router import (
        CopilotRequest, CopilotAction
    )
"""

from app.services.copilot.copilot_router import (
    generate_draft,
    CopilotRequest,
    CopilotAction,
)

__all__ = ["generate_draft", "CopilotRequest", "CopilotAction"]
