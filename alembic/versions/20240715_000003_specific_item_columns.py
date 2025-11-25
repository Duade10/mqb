"""Add specific_item columns for listing sub-pages

Revision ID: 20240715_000003
Revises: 20240701_000002
Create Date: 2024-07-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240715_000003"
down_revision = "20240701_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("faqs", sa.Column("specific_item", sa.String(length=255), nullable=True))
    op.add_column(
        "tutorials", sa.Column("specific_item", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "page_descriptions",
        sa.Column("specific_item", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("page_descriptions", "specific_item")
    op.drop_column("tutorials", "specific_item")
    op.drop_column("faqs", "specific_item")
