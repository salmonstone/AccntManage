"""add_proxy_label_enabled_mailbox_credentials

Revision ID: c996258fd7c6
Revises: b425d03ca2a7
Create Date: 2026-10-27 02:29:59.948379
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c996258fd7c6'
down_revision: str | None = 'b425d03ca2a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('mailboxes', sa.Column('encrypted_password', sa.Text(), nullable=True))
    op.add_column('mailboxes', sa.Column('client_id', sa.String(length=255), nullable=True))
    op.add_column('mailboxes', sa.Column('token_type', sa.String(length=50), nullable=True))
    op.add_column('proxies', sa.Column('label', sa.String(length=255), nullable=True))
    op.add_column('proxies', sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade() -> None:
    op.drop_column('proxies', 'enabled')
    op.drop_column('proxies', 'label')
    op.drop_column('mailboxes', 'token_type')
    op.drop_column('mailboxes', 'client_id')
    op.drop_column('mailboxes', 'encrypted_password')
