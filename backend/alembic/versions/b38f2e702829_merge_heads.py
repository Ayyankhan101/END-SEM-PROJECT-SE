"""Merge heads

Revision ID: b38f2e702829
Revises: 1b87bc29f48d, 2add_user_ownership
Create Date: 2026-04-26 20:01:34.596719

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b38f2e702829'
down_revision: Union[str, Sequence[str], None] = ('1b87bc29f48d', '2add_user_ownership')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
