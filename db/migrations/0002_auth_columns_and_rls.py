"""Add columns required by the API auth flow and make users RLS auth-safe.

Revision ID: 0002_auth_columns_and_rls
Revises: 0001_baseline
Create Date: 2026-07-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_auth_columns_and_rls"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These columns are used by the existing auth and profile endpoints but
    # were omitted from the UUID baseline.
    users_columns = (
        ("password_hash", sa.String(255), None),
        ("oauth_id", sa.String(255), None),
        ("is_verified", sa.Boolean(), "false"),
        ("is_active", sa.Boolean(), "true"),
        ("avatar_url", sa.String(255), None),
        ("xp", sa.Integer(), "0"),
        ("streak_count", sa.Integer(), "0"),
        ("streak_color", sa.String(50), "'emerald'"),
        ("last_active_date", sa.Date(), None),
        ("token_version", sa.Integer(), "1"),
        ("last_login", sa.DateTime(), None),
    )
    for name, column_type, default in users_columns:
        op.add_column(
            "users",
            sa.Column(name, column_type, nullable=True, server_default=default),
        )

    op.add_column(
        "tenants",
        sa.Column("plan", sa.String(), nullable=True, server_default="'free'"),
    )

    op.create_table(
        "verification_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_verification_codes_email", "verification_codes", ["email"]
    )

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute(
        "CREATE POLICY tenant_isolation ON users "
        "USING (current_setting('app.tenant_id', true) IS NULL "
        "OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (current_setting('app.tenant_id', true) IS NULL "
        "OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute(
        "CREATE POLICY tenant_isolation ON users "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.drop_index("ix_verification_codes_email", table_name="verification_codes")
    op.drop_table("verification_codes")
    op.drop_column("tenants", "plan")
    for name, _, _ in (
        ("last_login", None, None),
        ("token_version", None, None),
        ("last_active_date", None, None),
        ("streak_color", None, None),
        ("streak_count", None, None),
        ("xp", None, None),
        ("avatar_url", None, None),
        ("is_active", None, None),
        ("is_verified", None, None),
        ("oauth_id", None, None),
        ("password_hash", None, None),
    ):
        op.drop_column("users", name)
