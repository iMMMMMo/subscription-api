"""seed default FREE plan

Revision ID: ff8b69ca77e0
Revises: 214cfe5930ba
Create Date: 2025-12-27 03:01:10.308686

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff8b69ca77e0"
down_revision: Union[str, Sequence[str], None] = "214cfe5930ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO plans (name, request_limit, is_active)
        VALUES ('FREE', 100, true)
        ON CONFLICT (name) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
