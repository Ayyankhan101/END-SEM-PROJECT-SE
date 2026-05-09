"""add_user_security_columns

Revision ID: add_user_security_columns
Revises: 7e8fa1f1e4e0
Create Date: 2026-05-09 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_user_security_columns'
down_revision: Union[str, Sequence[str], None] = '7e8fa1f1e4e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('force_password_change', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('tokens_revoked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'tokens_revoked_at')
    op.drop_column('users', 'force_password_change')
