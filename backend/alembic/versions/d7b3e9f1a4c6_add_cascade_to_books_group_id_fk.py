"""add cascade to books group_id fk

Revision ID: d7b3e9f1a4c6
Revises: c4a9d6e3f2b8
Create Date: 2026-05-08 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d7b3e9f1a4c6"
down_revision: str | None = "c4a9d6e3f2b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("books_group_id_fkey", "books", type_="foreignkey")
    op.create_foreign_key(
        "books_group_id_fkey", "books", "groups",
        ["group_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("books_group_id_fkey", "books", type_="foreignkey")
    op.create_foreign_key(
        "books_group_id_fkey", "books", "groups",
        ["group_id"], ["id"],
    )
