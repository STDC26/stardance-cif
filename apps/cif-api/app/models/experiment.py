import uuid
from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(String, nullable=False, unique=True)
    asset_id = Column(UUID(as_uuid=True), nullable=False)
    asset_type = Column(String, nullable=False)
    experiment_name = Column(String, nullable=False)
    goal_metric = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")
    start_at = Column(TIMESTAMP(timezone=True), nullable=True)
    end_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),
                        server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    variants = relationship("ExperimentVariant", back_populates="experiment",
                            cascade="all, delete-orphan")
    assignments = relationship("ExperimentAssignment",
                               back_populates="experiment",
                               cascade="all, delete-orphan")


class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"
    __table_args__ = (
        CheckConstraint(
            "(surface_version_id IS NOT NULL AND qds_version_id IS NULL) OR "
            "(surface_version_id IS NULL AND qds_version_id IS NOT NULL)",
            name="ck_variant_single_version",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True),
                           ForeignKey("experiments.id"), nullable=False)
    variant_key = Column(String, nullable=False)
    surface_version_id = Column(UUID(as_uuid=True),
                                ForeignKey("surface_versions.id"),
                                nullable=True)
    qds_version_id = Column(UUID(as_uuid=True),
                            ForeignKey("qds_versions.id"), nullable=True)
    traffic_percentage = Column(Numeric(5, 2), nullable=False)
    is_control = Column(Boolean, default=False)
    status = Column(String, default="active")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="variants")
    assignments = relationship("ExperimentAssignment",
                               back_populates="variant")


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "session_id",
                         name="uq_experiment_session"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True),
                           ForeignKey("experiments.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True),
                        ForeignKey("experiment_variants.id"), nullable=False)
    session_id = Column(String, nullable=False)
    anonymous_user_id = Column(String, nullable=True)
    assigned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="assignments")
    variant = relationship("ExperimentVariant", back_populates="assignments")


class SignalAggregate(Base):
    __tablename__ = "signal_aggregates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_key = Column(String, nullable=False, unique=True)
    asset_id = Column(UUID(as_uuid=True), nullable=True)
    experiment_id = Column(UUID(as_uuid=True),
                           ForeignKey("experiments.id"), nullable=True)
    variant_id = Column(UUID(as_uuid=True),
                        ForeignKey("experiment_variants.id"), nullable=True)
    surface_version_id = Column(UUID(as_uuid=True),
                                ForeignKey("surface_versions.id"),
                                nullable=True)
    qds_version_id = Column(UUID(as_uuid=True),
                            ForeignKey("qds_versions.id"), nullable=True)
    asset_type = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Numeric(18, 6), nullable=False)
    window_type = Column(String, nullable=False)
    window_start = Column(TIMESTAMP(timezone=True), nullable=True)
    window_end = Column(TIMESTAMP(timezone=True), nullable=True)
    computed_at = Column(TIMESTAMP(timezone=True),
                         server_default=func.now())


class InsightReport(Base):
    __tablename__ = "insight_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(String, nullable=False, unique=True)
    asset_id = Column(UUID(as_uuid=True), nullable=True)
    experiment_id = Column(UUID(as_uuid=True),
                           ForeignKey("experiments.id"), nullable=True)
    report_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    payload_json = Column(JSONB, nullable=True)
    generated_at = Column(TIMESTAMP(timezone=True),
                          server_default=func.now())
    status = Column(String, default="active")
