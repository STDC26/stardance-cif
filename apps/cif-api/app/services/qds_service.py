import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.qds import (
    QDSAsset, QDSVersion, QDSFlow, QDSStep,
    QDSTransition, QDSOutcome, QDSScoringRule,
    QDSSession, QDSAnswer, QDSSessionStatus
)
from app.schemas.qds import QDSCreateIn
from app.core.slugify import slugify, unique_suffix


async def create_qds_asset(data: QDSCreateIn, db: AsyncSession) -> dict:
    base_slug = slugify(data.name)
    slug = f"{base_slug}-{unique_suffix()}"

    asset = QDSAsset(name=data.name, slug=slug)
    db.add(asset)
    await db.flush()

    version = QDSVersion(asset_id=asset.id, version_number=1, review_state="draft")
    db.add(version)
    await db.flush()

    flow = QDSFlow(version_id=version.id)
    db.add(flow)
    await db.flush()

    _STEP_TYPE_NORM = {
        "single_choice": "single_select",
        "multiple_choice": "multi_select",
    }

    # Create steps
    step_objects = []
    for step_in in data.steps:
        step = QDSStep(
            flow_id=flow.id,
            step_type=_STEP_TYPE_NORM.get(step_in.step_type, step_in.step_type),
            title=step_in.title,
            prompt=step_in.prompt,
            options=[o.model_dump() for o in step_in.options] if step_in.options else None,
            validation_rules=step_in.validation_rules,
            position=step_in.position,
        )
        db.add(step)
        step_objects.append(step)
    await db.flush()

    # Set entry step
    if step_objects:
        flow.entry_step_id = step_objects[0].id
    await db.flush()

    # Create outcomes
    outcome_objects = []
    for outcome_in in data.outcomes:
        outcome = QDSOutcome(
            flow_id=flow.id,
            label=outcome_in.label,
            qualification_status=outcome_in.qualification_status,
            score_band_min=outcome_in.score_band_min,
            score_band_max=outcome_in.score_band_max,
            routing_target=outcome_in.routing_target,
            message=outcome_in.message,
        )
        db.add(outcome)
        outcome_objects.append(outcome)
    await db.flush()

    # Create transitions
    for trans_in in data.transitions:
        from_step = step_objects[trans_in.from_step_position]
        to_step_id = (
            step_objects[trans_in.to_step_position].id
            if trans_in.to_step_position is not None else None
        )
        to_outcome_id = (
            outcome_objects[trans_in.to_outcome_index].id
            if trans_in.to_outcome_index is not None else None
        )
        transition = QDSTransition(
            flow_id=flow.id,
            from_step_id=from_step.id,
            to_step_id=to_step_id,
            to_outcome_id=to_outcome_id,
            condition=trans_in.condition,
            priority=trans_in.priority,
        )
        db.add(transition)

    # Create scoring rules
    for rule_in in data.scoring_rules:
        step_id = (
            step_objects[rule_in.step_position].id
            if rule_in.step_position is not None else None
        )
        rule = QDSScoringRule(
            flow_id=flow.id,
            step_id=step_id,
            answer_value=rule_in.answer_value,
            score=rule_in.score,
            description=rule_in.description,
        )
        db.add(rule)

    await db.commit()
    await db.refresh(asset)

    return {
        "id": str(asset.id),
        "name": asset.name,
        "slug": asset.slug,
        "version_id": str(version.id),
        "flow_id": str(flow.id),
        "review_state": version.review_state,
        "created_at": asset.created_at.isoformat(),
    }


async def resolve_qds(asset_id: uuid.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(QDSAsset).where(QDSAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return None

    result = await db.execute(
        select(QDSVersion)
        .where(QDSVersion.asset_id == asset_id)
        .order_by(QDSVersion.version_number.desc())
    )
    version = result.scalars().first()
    if not version:
        return None

    result = await db.execute(
        select(QDSFlow).where(QDSFlow.version_id == version.id)
    )
    flow = result.scalar_one_or_none()

    result = await db.execute(
        select(QDSStep).where(QDSStep.flow_id == flow.id).order_by(QDSStep.position)
    )
    steps = result.scalars().all()

    result = await db.execute(
        select(QDSOutcome).where(QDSOutcome.flow_id == flow.id)
    )
    outcomes = result.scalars().all()

    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "slug": asset.slug,
        "version_id": str(version.id),
        "version_number": version.version_number,
        "review_state": version.review_state,
        "flow": {
            "id": str(flow.id),
            "entry_step_id": str(flow.entry_step_id) if flow.entry_step_id else None,
            "steps": [
                {
                    "id": str(s.id),
                    "step_type": s.step_type,
                    "title": s.title,
                    "prompt": s.prompt,
                    "options": s.options,
                    "position": s.position,
                }
                for s in steps
            ],
            "outcomes": [
                {
                    "id": str(o.id),
                    "label": o.label,
                    "qualification_status": o.qualification_status,
                    "score_band_min": o.score_band_min,
                    "score_band_max": o.score_band_max,
                    "routing_target": o.routing_target,
                    "message": o.message,
                }
                for o in outcomes
            ],
        },
    }
