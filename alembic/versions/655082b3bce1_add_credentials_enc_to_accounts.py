"""add credentials_enc to accounts

Revision ID: 655082b3bce1
Revises: e1a2b3c4d5e6
Create Date: 2026-10-27 09:11:22.784125
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '655082b3bce1'
down_revision: Union[str, None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('credentials_enc', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'credentials_enc')
