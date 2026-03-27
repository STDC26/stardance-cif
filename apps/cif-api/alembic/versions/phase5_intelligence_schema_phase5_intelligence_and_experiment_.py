"""phase5 intelligence and experiment schema

Revision ID: phase5_intelligence_schema
Revises: 99fb6f1b3a66
Create Date: 2026-03-12 17:05:58.870065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'phase5_intelligence_schema'
down_revision: Union[str, Sequence[str], None] = '99fb6f1b3a66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # --- drop legacy objects with IF EXISTS (may not exist in fresh DB) ---
    op.execute("ALTER TABLE signal_events DROP CONSTRAINT IF EXISTS signal_events_experiment_id_fkey")
    op.execute("DROP TABLE IF EXISTS experiments")

    # --- create assets table (required by experiments, signal_aggregates, insight_reports) ---
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("asset_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # --- add experiment_id to signal_events (missing from initial schema) ---
    op.execute("ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS experiment_id UUID")

    # --- experiments ---
    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", sa.String(), nullable=False, unique=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("experiment_name", sa.String(), nullable=False),
        sa.Column("goal_metric", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False,
                  server_default="draft"),
        sa.Column("start_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("end_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("idx_experiments_asset_id", "experiments", ["asset_id"])
    op.create_index("idx_experiments_status", "experiments", ["status"])

    # Re-add FK from signal_events to new experiments table
    op.create_foreign_key(
        "signal_events_experiment_id_fkey", "signal_events",
        "experiments", ["experiment_id"], ["id"],
    )

    # --- experiment_variants ---
    op.create_table(
        "experiment_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("variant_key", sa.String(), nullable=False),
        sa.Column("surface_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("surface_versions.id"), nullable=True),
        sa.Column("qds_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("qds_versions.id"), nullable=True),
        sa.Column("traffic_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_control", sa.Boolean(), server_default="false"),
        sa.Column("status", sa.String(), server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_check_constraint(
        "ck_variant_single_version",
        "experiment_variants",
        "(surface_version_id IS NOT NULL AND qds_version_id IS NULL) OR "
        "(surface_version_id IS NULL AND qds_version_id IS NOT NULL)",
    )
    op.create_index(
        "idx_variants_experiment_id", "experiment_variants", ["experiment_id"]
    )

    # --- experiment_assignments ---
    op.create_table(
        "experiment_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiment_variants.id"), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("anonymous_user_id", sa.String(), nullable=True),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_experiment_session",
        "experiment_assignments",
        ["experiment_id", "session_id"],
    )
    op.create_index(
        "idx_assignments_variant", "experiment_assignments", ["variant_id"]
    )
    op.create_index(
        "idx_assignments_session", "experiment_assignments", ["session_id"]
    )

    # --- signal_aggregates ---
    op.create_table(
        "signal_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_key", sa.String(), nullable=False, unique=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiments.id"), nullable=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiment_variants.id"), nullable=True),
        sa.Column("surface_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("surface_versions.id"), nullable=True),
        sa.Column("qds_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("qds_versions.id"), nullable=True),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("metric_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("window_type", sa.String(), nullable=False),
        sa.Column("window_start", sa.TIMESTAMP(timezone=True),
                  nullable=True),
        sa.Column("window_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("idx_aggregate_asset", "signal_aggregates", ["asset_id"])
    op.create_index(
        "idx_aggregate_experiment", "signal_aggregates", ["experiment_id"]
    )
    op.create_index(
        "idx_aggregate_metric", "signal_aggregates", ["metric_name"]
    )
    op.create_index(
        "idx_aggregate_window",
        "signal_aggregates",
        ["window_start", "window_end"],
    )

    # --- insight_reports ---
    op.create_table(
        "insight_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", sa.String(), nullable=False, unique=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiments.id"), nullable=True),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("status", sa.String(), server_default="active"),
    )
    op.create_index("idx_insight_asset", "insight_reports", ["asset_id"])
    op.create_index(
        "idx_insight_experiment", "insight_reports", ["experiment_id"]
    )
    op.create_index(
        "idx_insight_report_type", "insight_reports", ["report_type"]
    )


def downgrade() -> None:
    op.drop_table("insight_reports")
    op.drop_table("signal_aggregates")
    op.drop_table("experiment_assignments")
    op.drop_table("experiment_variants")
    op.drop_table("experiments")

    # --- restore legacy experiments table ---
    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("surface_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("surfaces.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "signal_events_experiment_id_fkey", "signal_events",
        "experiments", ["experiment_id"], ["id"],
    )
