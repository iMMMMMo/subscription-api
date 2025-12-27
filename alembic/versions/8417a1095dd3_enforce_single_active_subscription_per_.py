"""enforce single active subscription per user

Revision ID: 8417a1095dd3
Revises: ff8b69ca77e0
Create Date: 2025-12-27 14:56:59.835523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8417a1095dd3'
down_revision: Union[str, Sequence[str], None] = 'ff8b69ca77e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        'ix_subscriptions_user_active',
        table_name='subscriptions',
        postgresql_where=sa.text('is_active = true'),
    )
    op.create_index(
        'ix_subscriptions_user_active',
        'subscriptions',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_subscriptions_user_active',
        table_name='subscriptions',
        postgresql_where=sa.text('is_active = true'),
    )
    op.create_index(
        'ix_subscriptions_user_active',
        'subscriptions',
        ['user_id'],
        unique=False,
        postgresql_where=sa.text('is_active = true'),
    )
