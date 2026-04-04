from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class QDSOptionIn(BaseModel):
    label: str
    value: str
    score_weight: float = 0.0


class QDSStepIn(BaseModel):
    step_type: str
    title: str
    prompt: str
    options: list[QDSOptionIn] | None = None
    validation_rules: dict[str, Any] | None = None
    position: int = 0


class QDSTransitionIn(BaseModel):
    from_step_position: int
    condition: dict[str, Any] | None = None
    to_step_position: int | None = None
    to_outcome_index: int | None = None
    priority: int = 0


class QDSOutcomeIn(BaseModel):
    label: str
    qualification_status: str
    score_band_min: float | None = None
    score_band_max: float | None = None
    routing_target: str | None = None
    message: str | None = None


class QDSScoringRuleIn(BaseModel):
    step_position: int | None = None
    answer_value: str | None = None
    score: float = 0.0
    description: str | None = None


class QDSCreateIn(BaseModel):
    name: str
    steps: list[QDSStepIn]
    transitions: list[QDSTransitionIn] = []
    outcomes: list[QDSOutcomeIn]
    scoring_rules: list[QDSScoringRuleIn] = []


class QDSStepOut(BaseModel):
    id: str
    step_type: str
    title: str
    prompt: str
    options: list[dict] | None
    position: int

    class Config:
        from_attributes = True


class QDSOutcomeOut(BaseModel):
    id: str
    label: str
    qualification_status: str
    score_band_min: float | None
    score_band_max: float | None
    routing_target: str | None
    message: str | None

    class Config:
        from_attributes = True


class QDSFlowOut(BaseModel):
    id: str
    entry_step_id: str | None
    steps: list[QDSStepOut]
    outcomes: list[QDSOutcomeOut]

    class Config:
        from_attributes = True


class QDSVersionOut(BaseModel):
    id: str
    asset_id: str
    version_number: int
    review_state: str
    reviewed_at: datetime | None
    published_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class QDSAssetOut(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class QDSResolvedOut(BaseModel):
    asset_id: str
    asset_name: str
    slug: str
    version_id: str
    version_number: int
    review_state: str
    flow: QDSFlowOut


class QDSAnswerIn(BaseModel):
    session_key: str
    step_id: str
    answer_value: Any


class QDSAnswerOut(BaseModel):
    session_id: str
    step_id: str
    next_step_id: str | None
    outcome: QDSOutcomeOut | None
    cumulative_score: float
    session_status: str


class QDSSessionOut(BaseModel):
    id: str
    asset_id: str
    version_id: str
    session_key: str
    status: str
    current_step_id: str | None
    cumulative_score: float
    outcome_id: str | None
    started_at: datetime
    completed_at: datetime | None
