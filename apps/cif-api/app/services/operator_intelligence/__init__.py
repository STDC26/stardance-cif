"""
CIF Operator Intelligence Package — Phase-6 Sprint-4

Provides AI-assisted interpretation of CIF platform data.
All insight generation uses the Retrieval Layer for context
and the AI Router for inference.

Governance: LLMs interpret only. CIF Core controls all actions.

Public interface:
    from app.services.operator_intelligence import generate_insight
    from app.services.operator_intelligence.insight_router import (
        InsightRequest, InsightType
    )
"""

from app.services.operator_intelligence.insight_router import (
    generate_insight,
    InsightRequest,
    InsightType,
)

__all__ = ["generate_insight", "InsightRequest", "InsightType"]
