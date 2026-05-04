"""add_lockout_fields

Revision ID: 1b87bc29f48d
Revises: 7e8fa1f1e4e0
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1b87bc29f48d'
down_revision: Union[str, Sequence[str], None] = '7e8fa1f1e4e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('lockout_until', sa.DateTime(), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'lockout_until')
    op.drop_column('users', 'failed_login_attempts')
