"""add consent email, faq links, and page descriptions"""

from alembic import op
import sqlalchemy as sa


revision = "20240701_000002"
down_revision = "20240101_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consent_logs", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("faq_translations", sa.Column("links", sa.JSON(), nullable=True))

    op.create_table(
        "page_descriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "page_description_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_description_id", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["page_description_id"], ["page_descriptions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "page_description_id",
            "language_code",
            name="uq_page_description_language",
        ),
    )


def downgrade() -> None:
    op.drop_table("page_description_translations")
    op.drop_table("page_descriptions")
    op.drop_column("faq_translations", "links")
    op.drop_column("consent_logs", "email")
