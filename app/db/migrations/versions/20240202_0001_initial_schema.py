"""Initial database schema for autojob-bot."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20240202_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the initial schema."""

    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True)
            if op.get_context().dialect.name == "postgresql"
            else sa.String(length=36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("remote", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description_html", sa.Text(), nullable=False),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(length=500), nullable=False, server_default=sa.text("''")),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
    )
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])

    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("skills", sa.Text(), nullable=False),
        sa.Column("keywords", sa.String(length=500), nullable=False),
        sa.Column("geo_preference", sa.String(length=255), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("resume_template_path", sa.String(length=500), nullable=False),
        sa.Column("cover_template_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True)
            if op.get_context().dialect.name == "postgresql"
            else sa.String(length=36),
            nullable=False,
        ),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_matches_score", "matches", ["score"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True)
            if op.get_context().dialect.name == "postgresql"
            else sa.String(length=36),
            nullable=False,
        ),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("resume_path", sa.String(length=500), nullable=False),
        sa.Column("cover_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    """Drop the initial schema."""

    op.drop_table("documents")
    op.drop_index("ix_matches_score", table_name="matches")
    op.drop_table("matches")
    op.drop_table("profiles")
    op.drop_index("ix_jobs_posted_at", table_name="jobs")
    op.drop_table("jobs")
