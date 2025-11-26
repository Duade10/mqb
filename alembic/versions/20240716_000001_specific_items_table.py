"""Create specific_items table

Revision ID: 20240716_000001
Revises: 20240715_000003
Create Date: 2024-07-16 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240716_000001"
down_revision = "20240715_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "specific_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["listings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "slug", name="uq_specific_item_slug"),
    )
    op.create_index(op.f("ix_specific_items_id"), "specific_items", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_specific_items_id"), table_name="specific_items")
    op.drop_table("specific_items")
