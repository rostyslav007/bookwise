"""add file_hash to books

Revision ID: a1b2c3d4e5f6
Revises: f9a5b3c7d1e2
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f9a5b3c7d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("books", sa.Column("file_hash", sa.String(64), nullable=True))
    op.create_index("ix_books_file_hash", "books", ["file_hash"])


def downgrade() -> None:
    op.drop_index("ix_books_file_hash", table_name="books")
    op.drop_column("books", "file_hash")
