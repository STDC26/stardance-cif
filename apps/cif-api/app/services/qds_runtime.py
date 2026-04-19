"""
QDS Flow Runtime Engine

Responsibilities:
  - Start a new QDS session
  - Resolve the current step for a session
  - Accept and validate an answer
  - Evaluate branch transitions
  - Accumulate score
  - Detect session completion
  - Resolve terminal outcome

This engine is deterministic and version-bound.
It must not depend on surface rendering in any way.
"""

import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.qds import (
    QDSAsset, QDSVersion, QDSFlow, QDSStep,
    QDSTransition, QDSOutcome, QDSScoringRule,
    QDSSession, QDSAnswer, QDSSessionStatus,
)
from app.services.qds_signal_emitter import (
    emit_diagnostic_start,
    emit_step_view,
    emit_answer_submitted,
    emit_branch_selected,
    emit_diagnostic_complete,
    emit_qualification_result,
)


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

async def start_session(
    asset_id: uuid.UUID,
    session_key: str,
    device_metadata: dict | None,
    db: AsyncSession,
) -> dict:
    """
    Start a new QDS session on the latest published version of an asset.
    If a session with this key already exists, return it (idempotent).
    """
    # Check for existing session
    result = await db.execute(
        select(QDSSession).where(
            QDSSession.asset_id == asset_id,
            QDSSession.session_key == session_key,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return await _session_state(existing, db)

    # Resolve latest published version
    version = await _resolve_active_version(asset_id, db)

    # Resolve flow
    result = await db.execute(
        select(QDSFlow).where(QDSFlow.version_id == version.id)
    )
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=422, detail="QDS has no flow defined")

    # Resolve entry step
    if not flow.entry_step_id:
        raise HTTPException(status_code=422, detail="QDS flow has no entry step")

    session = QDSSession(
        asset_id=asset_id,
        version_id=version.id,
        flow_id=flow.id,
        session_key=session_key,
        status=QDSSessionStatus.in_progress,
        current_step_id=flow.entry_step_id,
        cumulative_score=0.0,
        device_metadata=device_metadata,
    )
    db.add(session)
    await db.flush()

    # Emit signals
    await emit_diagnostic_start(
        db=db,
        asset_id=asset_id,
        version_id=version.id,
        flow_id=flow.id,
        session_key=session_key,
        entry_step_id=flow.entry_step_id,
        device_metadata=device_metadata,
    )

    # Load entry step for step_view signal
    entry_result = await db.execute(
        select(QDSStep).where(QDSStep.id == flow.entry_step_id)
    )
    entry_step = entry_result.scalar_one_or_none()
    if entry_step:
        await emit_step_view(
            db=db,
            asset_id=asset_id,
            version_id=version.id,
            flow_id=flow.id,
            session_key=session_key,
            step_id=flow.entry_step_id,
            step_type=entry_step.step_type if isinstance(entry_step.step_type, str) else entry_step.step_type.value,
            step_title=entry_step.title,
            step_position=entry_step.position,
            journey_id=(device_metadata or {}).get("journey_id") if device_metadata else None,
        )

    await db.commit()
    await db.refresh(session)

    return await _session_state(session, db)


async def get_session(
    asset_id: uuid.UUID,
    session_key: str,
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(QDSSession).where(
            QDSSession.asset_id == asset_id,
            QDSSession.session_key == session_key,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await _session_state(session, db)


# ---------------------------------------------------------------------------
# Answer Submission + Branch Evaluation
# ---------------------------------------------------------------------------

async def submit_answer(
    asset_id: uuid.UUID,
    session_key: str,
    step_id: uuid.UUID,
    answer_value: any,
    db: AsyncSession,
) -> dict:
    """
    Accept an answer for the current step.
    Evaluate branching logic.
    Accumulate score.
    Advance session to next step or resolve outcome.
    """
    # Load session
    result = await db.execute(
        select(QDSSession).where(
            QDSSession.asset_id == asset_id,
            QDSSession.session_key == session_key,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_status = session.status if isinstance(session.status, str) else session.status.value
    if session_status != "in_progress":
        raise HTTPException(
            status_code=422,
            detail=f"Session is already {session_status} — cannot accept answers"
        )

    # Validate step matches current step
    if str(session.current_step_id) != str(step_id):
        raise HTTPException(
            status_code=422,
            detail=f"Expected current step {session.current_step_id}, got {step_id}"
        )

    # Load current step
    result = await db.execute(
        select(QDSStep).where(QDSStep.id == step_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    # Validate answer
    answer_value = _validate_answer(step, answer_value)

    # Calculate score contribution
    score = await _calculate_score(
        session.flow_id, step_id, answer_value, db
    )

    # Persist answer
    answer = QDSAnswer(
        session_id=session.id,
        step_id=step_id,
        answer_value=answer_value if isinstance(answer_value, (dict, list)) else str(answer_value),
        score_contribution=score,
    )
    db.add(answer)
    session.cumulative_score += score

    # Evaluate next step or outcome
    next_step_id, outcome_id = await _evaluate_transitions(
        session.flow_id, step_id, answer_value, session.cumulative_score, db
    )

    # Emit answer_submitted signal
    await emit_answer_submitted(
        db=db,
        asset_id=session.asset_id,
        version_id=session.version_id,
        flow_id=session.flow_id,
        session_key=session_key,
        step_id=step_id,
        answer_value=answer_value,
        score_contribution=score,
        cumulative_score=session.cumulative_score,
        step_position=step.position,
        journey_id=session.device_metadata.get("journey_id") if session.device_metadata else None,
    )

    # Emit branch_selected if a transition fired
    if next_step_id or outcome_id:
        await emit_branch_selected(
            db=db,
            asset_id=session.asset_id,
            version_id=session.version_id,
            flow_id=session.flow_id,
            session_key=session_key,
            from_step_id=step_id,
            to_step_id=next_step_id,
            to_outcome_id=outcome_id,
            condition=None,
        )

    if outcome_id:
        # Terminal — session complete
        session.status = QDSSessionStatus.completed
        session.outcome_id = outcome_id
        session.completed_at = datetime.utcnow()
        session.current_step_id = None
    elif next_step_id:
        session.current_step_id = next_step_id
        # Emit step_view for the next step
        result = await db.execute(
            select(QDSStep).where(QDSStep.id == next_step_id)
        )
        next_step = result.scalar_one_or_none()
        if next_step:
            await emit_step_view(
                db=db,
                asset_id=session.asset_id,
                version_id=session.version_id,
                flow_id=session.flow_id,
                session_key=session_key,
                step_id=next_step_id,
                step_type=next_step.step_type if isinstance(next_step.step_type, str) else next_step.step_type.value,
                step_title=next_step.title,
                step_position=next_step.position,
                journey_id=session.device_metadata.get("journey_id") if session.device_metadata else None,
            )
    else:
        # No transition defined — auto-advance to score-based outcome
        outcome_id = await _resolve_outcome_by_score(
            session.flow_id, session.cumulative_score, db
        )
        session.status = QDSSessionStatus.completed
        session.outcome_id = outcome_id
        session.completed_at = datetime.utcnow()
        session.current_step_id = None

    # Emit completion signals if session is now complete
    session_status_val = session.status if isinstance(session.status, str) else session.status.value
    if session_status_val == "completed" and session.outcome_id:
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count(QDSAnswer.id)).where(
                QDSAnswer.session_id == session.id
            )
        )
        answer_count = count_result.scalar() or 0

        outcome_result = await db.execute(
            select(QDSOutcome).where(QDSOutcome.id == session.outcome_id)
        )
        resolved_outcome = outcome_result.scalar_one_or_none()

        await emit_diagnostic_complete(
            db=db,
            asset_id=session.asset_id,
            version_id=session.version_id,
            flow_id=session.flow_id,
            session_key=session_key,
            outcome_id=session.outcome_id,
            cumulative_score=session.cumulative_score,
            total_steps_answered=answer_count,
        )

        if resolved_outcome:
            qs = resolved_outcome.qualification_status
            await emit_qualification_result(
                db=db,
                asset_id=session.asset_id,
                version_id=session.version_id,
                flow_id=session.flow_id,
                session_key=session_key,
                outcome_id=session.outcome_id,
                qualification_status=qs if isinstance(qs, str) else qs.value,
                score=session.cumulative_score,
                routing_target=resolved_outcome.routing_target,
                outcome_label=resolved_outcome.label,
                journey_id=session.device_metadata.get("journey_id") if session.device_metadata else None,
            )

    await db.commit()
    await db.refresh(session)

    return await _session_state(session, db)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

async def _resolve_active_version(
    asset_id: uuid.UUID, db: AsyncSession
) -> QDSVersion:
    """
    Return the version active in production deployment.
    Falls back to latest published, then latest draft for testing.
    This ensures runtime is deployment-bound, not just latest-version-bound.
    """
    from app.models.qds import QDSDeployment
    result = await db.execute(
        select(QDSDeployment).where(
            QDSDeployment.asset_id == asset_id,
            QDSDeployment.environment == "production",
            QDSDeployment.status == "active",
        )
    )
    deployment = result.scalar_one_or_none()
    if deployment:
        result = await db.execute(
            select(QDSVersion).where(QDSVersion.id == deployment.version_id)
        )
        version = result.scalar_one_or_none()
        if version:
            return version

    # Fallback: latest published
    result = await db.execute(
        select(QDSVersion)
        .where(
            QDSVersion.asset_id == asset_id,
            QDSVersion.review_state == "published",
        )
        .order_by(QDSVersion.version_number.desc())
    )
    version = result.scalars().first()
    if version:
        return version

    # Fallback for testing: latest draft
    result = await db.execute(
        select(QDSVersion)
        .where(QDSVersion.asset_id == asset_id)
        .order_by(QDSVersion.version_number.desc())
    )
    version = result.scalars().first()
    if not version:
        raise HTTPException(status_code=404, detail="No version found for QDS asset")
    return version


def _validate_answer(step: QDSStep, answer_value: any) -> any:
    """
    Validate answer against step type and validation rules.
    Returns normalized answer value.
    """
    step_type = step.step_type if isinstance(step.step_type, str) else step.step_type.value

    if step_type in ("single_select", "yes_no"):
        if step.options:
            valid_values = [o["value"] for o in step.options]
            if str(answer_value) not in valid_values:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid answer '{answer_value}'. Valid: {valid_values}"
                )
        return str(answer_value)

    if step_type == "multi_select":
        if not isinstance(answer_value, list):
            answer_value = [answer_value]
        if step.options:
            valid_values = [o["value"] for o in step.options]
            for v in answer_value:
                if v not in valid_values:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid selection '{v}'. Valid: {valid_values}"
                    )
        return answer_value

    if step_type == "numeric_input":
        try:
            val = float(answer_value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Numeric answer required")
        rules = step.validation_rules or {}
        if "min" in rules and val < rules["min"]:
            raise HTTPException(status_code=422, detail=f"Value below minimum {rules['min']}")
        if "max" in rules and val > rules["max"]:
            raise HTTPException(status_code=422, detail=f"Value above maximum {rules['max']}")
        return val

    if step_type == "text_input":
        rules = step.validation_rules or {}
        if rules.get("required") and not str(answer_value).strip():
            raise HTTPException(status_code=422, detail="Answer is required")
        return str(answer_value)

    if step_type == "informational":
        return "acknowledged"

    return answer_value


async def _calculate_score(
    flow_id: uuid.UUID,
    step_id: uuid.UUID,
    answer_value: any,
    db: AsyncSession,
) -> float:
    """
    Look up scoring rules for this step and answer value.
    Returns the score contribution.
    """
    answer_str = str(answer_value) if not isinstance(answer_value, list) else None

    result = await db.execute(
        select(QDSScoringRule).where(
            QDSScoringRule.flow_id == flow_id,
            QDSScoringRule.step_id == step_id,
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        if rule.answer_value is None:
            # Step-level weight — always applies
            return rule.score
        if answer_str and rule.answer_value == answer_str:
            return rule.score

    # Multi-select: sum matching rules
    if isinstance(answer_value, list):
        total = 0.0
        for v in answer_value:
            for rule in rules:
                if rule.answer_value == str(v):
                    total += rule.score
        return total

    return 0.0


async def _evaluate_transitions(
    flow_id: uuid.UUID,
    from_step_id: uuid.UUID,
    answer_value: any,
    cumulative_score: float,
    db: AsyncSession,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """
    Evaluate conditional transitions from the current step.
    Returns (next_step_id, outcome_id) — one will be None.
    Priority-ordered. First matching condition wins.
    Unconditional transitions (condition=None) are fallbacks.
    """
    result = await db.execute(
        select(QDSTransition)
        .where(
            QDSTransition.flow_id == flow_id,
            QDSTransition.from_step_id == from_step_id,
        )
        .order_by(QDSTransition.priority.desc())
    )
    transitions = result.scalars().all()

    fallback_transition = None

    for t in transitions:
        if not t.condition:
            fallback_transition = t
            continue

        if _evaluate_condition(t.condition, answer_value, cumulative_score):
            return t.to_step_id, t.to_outcome_id

    if fallback_transition:
        return fallback_transition.to_step_id, fallback_transition.to_outcome_id

    return None, None


def _evaluate_condition(
    condition: dict,
    answer_value: any,
    cumulative_score: float,
) -> bool:
    """
    Evaluate a single condition dict.

    Supported condition shapes:
      {"answer_value": "yes"}
      {"answer_value": "yes", "operator": "eq"}
      {"score_gte": 10.0}
      {"score_lt": 5.0}
      {"answer_in": ["a", "b"]}
    """
    if "answer_value" in condition:
        op = condition.get("operator", "eq")
        target = condition["answer_value"]
        if op == "eq":
            return str(answer_value) == str(target)
        if op == "neq":
            return str(answer_value) != str(target)

    if "answer_in" in condition:
        values = condition["answer_in"]
        if isinstance(answer_value, list):
            return any(v in values for v in answer_value)
        return str(answer_value) in values

    if "score_gte" in condition:
        return cumulative_score >= condition["score_gte"]

    if "score_lt" in condition:
        return cumulative_score < condition["score_lt"]

    return False


async def _resolve_outcome_by_score(
    flow_id: uuid.UUID,
    cumulative_score: float,
    db: AsyncSession,
) -> uuid.UUID | None:
    """
    When no explicit transition routes to an outcome, match by score band.
    """
    result = await db.execute(
        select(QDSOutcome).where(QDSOutcome.flow_id == flow_id)
    )
    outcomes = result.scalars().all()

    for outcome in outcomes:
        if outcome.score_band_min is not None and outcome.score_band_max is not None:
            if outcome.score_band_min <= cumulative_score <= outcome.score_band_max:
                return outcome.id

    # Fallback: return first outcome
    return outcomes[0].id if outcomes else None


async def _session_state(session: QDSSession, db: AsyncSession) -> dict:
    """
    Serialize current session state for API response.
    """
    current_step = None
    if session.current_step_id:
        result = await db.execute(
            select(QDSStep).where(QDSStep.id == session.current_step_id)
        )
        step = result.scalar_one_or_none()
        if step:
            current_step = {
                "id": str(step.id),
                "step_type": step.step_type if isinstance(step.step_type, str) else step.step_type.value,
                "title": step.title,
                "prompt": step.prompt,
                "options": step.options,
                "position": step.position,
            }

    outcome = None
    if session.outcome_id:
        result = await db.execute(
            select(QDSOutcome).where(QDSOutcome.id == session.outcome_id)
        )
        o = result.scalar_one_or_none()
        if o:
            outcome = {
                "id": str(o.id),
                "label": o.label,
                "qualification_status": o.qualification_status if isinstance(o.qualification_status, str) else o.qualification_status.value,
                "score_band_min": o.score_band_min,
                "score_band_max": o.score_band_max,
                "routing_target": o.routing_target,
                "message": o.message,
            }

    return {
        "session_id": str(session.id),
        "session_key": session.session_key,
        "asset_id": str(session.asset_id),
        "version_id": str(session.version_id),
        "status": session.status if isinstance(session.status, str) else session.status.value,
        "current_step": current_step,
        "cumulative_score": session.cumulative_score,
        "outcome": outcome,
        "started_at": session.started_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }
