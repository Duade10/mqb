"""create tables"""

from alembic import op
import sqlalchemy as sa

revision = "20240101_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "consent_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("listing_id", "version", name="uq_template_version"),
    )

    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "tutorials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "consent_template_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["consent_templates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("template_id", "language_code", name="uq_template_language"),
    )

    op.create_table(
        "faq_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("faq_id", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("question", sa.String(length=255), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["faq_id"], ["faqs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("faq_id", "language_code", name="uq_faq_language"),
    )

    op.create_table(
        "tutorial_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutorial_id", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tutorial_id"], ["tutorials.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tutorial_id", "language_code", name="uq_tutorial_language"),
    )

    op.create_table(
        "consent_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("decision", sa.String(length=10), nullable=False),
        sa.Column("ip_address", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["consent_templates.id"], ondelete="SET NULL"),
    )

def downgrade() -> None:
    op.drop_table("consent_logs")
    op.drop_table("tutorial_translations")
    op.drop_table("faq_translations")
    op.drop_table("consent_template_translations")
    op.drop_table("admin_users")
    op.drop_table("tutorials")
    op.drop_table("faqs")
    op.drop_table("consent_templates")
    op.drop_table("listings")
