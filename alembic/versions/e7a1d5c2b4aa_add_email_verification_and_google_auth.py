"""add email verification and google auth

Revision ID: e7a1d5c2b4aa
Revises: c3451225d071
Create Date: 2026-05-15 18:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7a1d5c2b4aa"
down_revision = "c3451225d071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("verification_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(), nullable=True),
    )
    op.alter_column("users", "password_hash", existing_type=sa.String(), nullable=True)
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)

    # Keep existing local accounts usable after rollout.
    op.execute("UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE")
    op.alter_column("users", "is_verified", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.alter_column("users", "password_hash", existing_type=sa.String(), nullable=False)
    op.drop_column("users", "google_sub")
    op.drop_column("users", "verification_sent_at")
    op.drop_column("users", "verified_at")
    op.drop_column("users", "is_verified")
