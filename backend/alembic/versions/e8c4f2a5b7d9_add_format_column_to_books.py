"""add format column to books

Revision ID: e8c4f2a5b7d9
Revises: d7b3e9f1a4c6
Create Date: 2026-05-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8c4f2a5b7d9"
down_revision: str | None = "d7b3e9f1a4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("books", sa.Column("format", sa.String(), nullable=False, server_default="pdf"))


def downgrade() -> None:
    op.drop_column("books", "format")
