"""
CIF Retrieval Layer — Phase-6 Sprint-3

Provides structured platform knowledge to the AI inference system.
All modules are READ-ONLY. No writes occur in this package.

Public interface:
    from app.services.retrieval import build_context, RetrievalRequest

    context = await build_context(
        request=RetrievalRequest(
            asset_id="uuid",
            experiment_id="uuid",
            include_signals=True,
        ),
        db=session,
    )
"""

from app.services.retrieval.context_builder import build_context, RetrievalRequest

__all__ = ["build_context", "RetrievalRequest"]
