"""
users_auth_sessions.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("login", sa.String(length=254), nullable=False),
        sa.Column("login_normalized", sa.String(length=254), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0 AND display_name = trim(display_name)",
            name=op.f("ck_users_display_name_trimmed"),
        ),
        sa.CheckConstraint(
            "length(trim(login)) > 0 AND login = trim(login)",
            name=op.f("ck_users_login_trimmed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("login_normalized", name=op.f("uq_users_login_normalized")),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("csrf_token", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "expires_at > created_at", name=op.f("ck_auth_sessions_expiry_order")
        ),
        sa.CheckConstraint(
            "octet_length(csrf_token) = 32", name=op.f("ck_auth_sessions_csrf_length")
        ),
        sa.CheckConstraint(
            "octet_length(token_hash) = 32", name=op.f("ck_auth_sessions_token_length")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_sessions_token_hash")),
    )
    op.create_index(
        "ix_sessions_expiry",
        "auth_sessions",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_sessions_revoked",
        "auth_sessions",
        ["revoked_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NOT NULL"),
    )
    op.create_index(
        "ix_sessions_user_expiry",
        "auth_sessions",
        ["user_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade():
    op.drop_index(
        "ix_sessions_user_expiry",
        table_name="auth_sessions",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_index(
        "ix_sessions_revoked",
        table_name="auth_sessions",
        postgresql_where=sa.text("revoked_at IS NOT NULL"),
    )
    op.drop_index(
        "ix_sessions_expiry",
        table_name="auth_sessions",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_table("auth_sessions")
    op.drop_table("users")
