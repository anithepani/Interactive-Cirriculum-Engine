"""Add avatar and streak fields to User

Revision ID: 30965f7e6314
Revises: f80c7b0ca147
Create Date: 2026-07-22 08:41:15.876954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '30965f7e6314'
down_revision: Union[str, Sequence[str], None] = 'f80c7b0ca147'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('avatar_url', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('streak_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('users', sa.Column('streak_color', sa.String(length=50), server_default="'emerald'", nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'streak_color')
    op.drop_column('users', 'streak_count')
    op.drop_column('users', 'avatar_url')
    # ### end Alembic commands ###
