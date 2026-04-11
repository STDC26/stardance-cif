import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base


class QDSStepType(str, PyEnum):
    single_select = "single_select"
    multi_select = "multi_select"
    text_input = "text_input"
    numeric_input = "numeric_input"
    yes_no = "yes_no"
    informational = "informational"
    terminal_outcome = "terminal_outcome"


class QDSQualificationStatus(str, PyEnum):
    high_fit = "high_fit"
    medium_fit = "medium_fit"
    low_fit = "low_fit"
    not_qualified = "not_qualified"
    qualified = "qualified"
    warm = "warm"


class QDSSessionStatus(str, PyEnum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class QDSAsset(Base):
    """Top-level QDS deployable asset. Registered in CIF Core."""
    __tablename__ = "qds_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("QDSVersion", back_populates="asset", cascade="all, delete-orphan")


class QDSVersion(Base):
    """Versioned snapshot of a QDS asset. Plugs into CIF Core lifecycle."""
    __tablename__ = "qds_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("qds_assets.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    review_state = Column(String, default="draft")
    reviewed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("QDSAsset", back_populates="versions")
    flow = relationship("QDSFlow", back_populates="version", uselist=False,
                        cascade="all, delete-orphan")


class QDSFlow(Base):
    """The logical flow definition for a QDS version."""
    __tablename__ = "qds_flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("qds_versions.id"), nullable=False)
    entry_step_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    version = relationship("QDSVersion", back_populates="flow")
    steps = relationship("QDSStep", back_populates="flow", cascade="all, delete-orphan",
                         order_by="QDSStep.position")
    transitions = relationship("QDSTransition", back_populates="flow",
                                cascade="all, delete-orphan")
    outcomes = relationship("QDSOutcome", back_populates="flow",
                             cascade="all, delete-orphan")
    scoring_rules = relationship("QDSScoringRule", back_populates="flow",
                                  cascade="all, delete-orphan")


class QDSStep(Base):
    """A single question or interaction state in a QDS flow."""
    __tablename__ = "qds_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("qds_flows.id"), nullable=False)
    step_type = Column(
        SAEnum(QDSStepType, name="qds_step_type_enum"),
        nullable=False
    )
    title = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)          # [{label, value, score_weight}]
    validation_rules = Column(JSON, nullable=True)  # {required, min, max}
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    flow = relationship("QDSFlow", back_populates="steps")


class QDSTransition(Base):
    """Conditional routing between steps."""
    __tablename__ = "qds_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("qds_flows.id"), nullable=False)
    from_step_id = Column(UUID(as_uuid=True), ForeignKey("qds_steps.id"), nullable=False)
    to_step_id = Column(UUID(as_uuid=True), ForeignKey("qds_steps.id"), nullable=True)
    to_outcome_id = Column(UUID(as_uuid=True), ForeignKey("qds_outcomes.id"), nullable=True)
    condition = Column(JSON, nullable=True)  # {answer_value, operator, threshold}
    priority = Column(Integer, default=0)

    flow = relationship("QDSFlow", back_populates="transitions")


class QDSOutcome(Base):
    """Terminal result state for a QDS flow."""
    __tablename__ = "qds_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("qds_flows.id"), nullable=False)
    label = Column(String, nullable=False)
    qualification_status = Column(
        SAEnum(QDSQualificationStatus, name="qds_qualification_status_enum"),
        nullable=False
    )
    score_band_min = Column(Float, nullable=True)
    score_band_max = Column(Float, nullable=True)
    routing_target = Column(String, nullable=True)
    message = Column(Text, nullable=True)

    flow = relationship("QDSFlow", back_populates="outcomes")


class QDSScoringRule(Base):
    """Scoring weights applied at flow level."""
    __tablename__ = "qds_scoring_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("qds_flows.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("qds_steps.id"), nullable=True)
    answer_value = Column(String, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    description = Column(String, nullable=True)

    flow = relationship("QDSFlow", back_populates="scoring_rules")


class QDSDeployment(Base):
    """QDS deployment record. Mirrors surface deployment model."""
    __tablename__ = "qds_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("qds_assets.id"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("qds_versions.id"), nullable=False)
    environment = Column(String, nullable=False)  # preview / staging / production
    status = Column(String, default="pending")    # pending / active / inactive / failed
    deployed_by = Column(String, nullable=True)
    deployed_at = Column(DateTime, default=datetime.utcnow)
    deactivated_at = Column(DateTime, nullable=True)
    slug = Column(String, nullable=True)


class QDSSession(Base):
    """Runtime session tracking for a QDS flow completion."""
    __tablename__ = "qds_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("qds_assets.id"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("qds_versions.id"), nullable=False)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("qds_flows.id"), nullable=False)
    session_key = Column(String, nullable=False, index=True)
    status = Column(
        SAEnum(QDSSessionStatus, name="qds_session_status_enum"),
        default=QDSSessionStatus.in_progress
    )
    current_step_id = Column(UUID(as_uuid=True), nullable=True)
    cumulative_score = Column(Float, default=0.0)
    outcome_id = Column(UUID(as_uuid=True), ForeignKey("qds_outcomes.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    device_metadata = Column(JSON, nullable=True)


class QDSAnswer(Base):
    """Individual answer submitted within a QDS session."""
    __tablename__ = "qds_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("qds_sessions.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("qds_steps.id"), nullable=False)
    answer_value = Column(JSON, nullable=False)   # string, list, number depending on step_type
    score_contribution = Column(Float, default=0.0)
    submitted_at = Column(DateTime, default=datetime.utcnow)
