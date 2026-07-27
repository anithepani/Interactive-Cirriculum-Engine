"""Add token_version to User

Revision ID: a1b2c3d4e5f6
Revises: 30965f7e6314
Create Date: 2026-07-27 06:30:00.000000

Closes the schema-drift gap introduced in 591d00a ("feat: update database
models with pgvector support"), which added ``token_version`` to the Python
``User`` model (read by every auth path via ``user.token_version`` and the
``"tv"`` JWT claim) but never shipped a matching migration. Without this
column, every ``SELECT ... FROM users`` raises ``UndefinedColumnError`` and
signup/login return a 500 with a non-JSON body, breaking the frontend.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "30965f7e6314"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='1' mirrors the ORM (models.py: User.token_version) so
    # pre-existing rows (and any inserted outside the ORM) get a sane value
    # and existing JWTs stay valid until the user rotates their password.
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_version")
