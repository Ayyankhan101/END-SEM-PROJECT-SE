"""add user_id to containers for ownership

Revision ID: 2add_user_ownership
Revises: 20260418_new_models
Create Date: 2026-04-26 10:59:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '2add_user_ownership'
down_revision = '20260418_new_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('containers', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_containers_user_id', 'containers', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_containers_user_id', 'containers', type_='foreignkey')
    op.drop_column('containers', 'user_id')
