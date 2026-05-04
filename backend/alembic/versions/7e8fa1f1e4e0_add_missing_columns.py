"""add_missing_columns

Revision ID: 7e8fa1f1e4e0
Revises: 20260418_new_models
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7e8fa1f1e4e0'
down_revision: Union[str, Sequence[str], None] = '20260418_new_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add group and is_favorite to containers
    op.add_column('containers', sa.Column('group', sa.String(), nullable=True, server_default='default'))
    op.add_column('containers', sa.Column('is_favorite', sa.Integer(), nullable=True, server_default='0'))
    
    # Add hash_chain to audit_logs
    op.add_column('audit_logs', sa.Column('hash_chain', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('audit_logs', 'hash_chain')
    op.drop_column('containers', 'is_favorite')
    op.drop_column('containers', 'group')
