"""merge heads

Revision ID: f80c7b0ca147
Revises: bc5a0d40884f, bd848bdbbd58
Create Date: 2026-07-22 08:38:50.588306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f80c7b0ca147'
down_revision: Union[str, Sequence[str], None] = ('bc5a0d40884f', 'bd848bdbbd58')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
