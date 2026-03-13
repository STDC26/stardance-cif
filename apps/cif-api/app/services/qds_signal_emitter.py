"""
QDS Signal Emitter

Emits canonical QDS signals through the existing CIF signal engine.
QDS signals flow into the same signal_events table as surface signals.
This is intentional — one signal pipeline for all CIF asset types.

Called internally by the QDS runtime after each significant event.
Not called directly by the client.

Column mapping:
  signal_events.surface_id  → QDS asset_id (FK removed, nullable)
  signal_events.event_type  → one of the 6 QDS event types
  signal_events.event_data  → structured dict with asset_type, flow_id, etc.
  signal_events.session_id  → QDS session_key
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import SignalEvent


async def emit(
    db: AsyncSession,
    event_type: str,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    step_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Emit a single QDS signal event into the CIF signal_events table.
    Silently swallows errors — signal emission must never crash the runtime.
    """
    try:
        event = SignalEvent(
            surface_id=asset_id,
            event_type=event_type,
            session_id=session_key,
            event_data={
                "asset_type": "qds",
                "version_id": str(version_id),
                "flow_id": str(flow_id),
                "step_id": str(step_id) if step_id else None,
                **(metadata or {}),
            },
        )
        db.add(event)
        await db.flush()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            f"QDS signal emission failed [{event_type}]: {exc}"
        )


async def emit_diagnostic_start(
    db: AsyncSession,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    entry_step_id: uuid.UUID | None,
    device_metadata: dict | None,
) -> None:
    await emit(
        db=db,
        event_type="diagnostic_start",
        asset_id=asset_id,
        version_id=version_id,
        flow_id=flow_id,
        session_key=session_key,
        step_id=entry_step_id,
        metadata={
            "entry_step_id": str(entry_step_id) if entry_step_id else None,
            "device_metadata": device_metadata or {},
        },
    )


async def emit_step_view(
    db: AsyncSession,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    step_id: uuid.UUID,
    step_type: str,
    step_title: str,
) -> None:
    await emit(
        db=db,
        event_type="step_view",
        asset_id=asset_id,
        version_id=version_id,
        flow_id=flow_id,
        session_key=session_key,
        step_id=step_id,
        metadata={
            "step_type": step_type,
            "step_title": step_title,
        },
    )


async def emit_answer_submitted(
    db: AsyncSession,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    step_id: uuid.UUID,
    answer_value: any,
    score_contribution: float,
    cumulative_score: float,
) -> None:
    await emit(
        db=db,
        event_type="answer_submitted",
        asset_id=asset_id,
        version_id=version_id,
        flow_id=flow_id,
        session_key=session_key,
        step_id=step_id,
        metadata={
            "answer_value": answer_value if isinstance(answer_value, (str, int, float, list)) else str(answer_value),
            "score_contribution": score_contribution,
            "cumulative_score": cumulative_score,
        },
    )


async def emit_branch_selected(
    db: AsyncSession,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    from_step_id: uuid.UUID,
    to_step_id: uuid.UUID | None,
    to_outcome_id: uuid.UUID | None,
    condition: dict | None,
) -> None:
    await emit(
        db=db,
        event_type="branch_selected",
        asset_id=asset_id,
        version_id=version_id,
        flow_id=flow_id,
        session_key=session_key,
        step_id=from_step_id,
        metadata={
            "from_step_id": str(from_step_id),
            "to_step_id": str(to_step_id) if to_step_id else None,
            "to_outcome_id": str(to_outcome_id) if to_outcome_id else None,
            "condition": condition,
        },
    )


async def emit_diagnostic_complete(
    db: AsyncSession,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    outcome_id: uuid.UUID,
    cumulative_score: float,
    total_steps_answered: int,
) -> None:
    await emit(
        db=db,
        event_type="diagnostic_complete",
        asset_id=asset_id,
        version_id=version_id,
        flow_id=flow_id,
        session_key=session_key,
        metadata={
            "outcome_id": str(outcome_id),
            "cumulative_score": cumulative_score,
            "total_steps_answered": total_steps_answered,
        },
    )


async def emit_qualification_result(
    db: AsyncSession,
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    flow_id: uuid.UUID,
    session_key: str,
    outcome_id: uuid.UUID,
    qualification_status: str,
    score: float,
    routing_target: str | None,
) -> None:
    await emit(
        db=db,
        event_type="qualification_result",
        asset_id=asset_id,
        version_id=version_id,
        flow_id=flow_id,
        session_key=session_key,
        metadata={
            "outcome_id": str(outcome_id),
            "qualification_status": qualification_status,
            "score": score,
            "routing_target": routing_target,
        },
    )
