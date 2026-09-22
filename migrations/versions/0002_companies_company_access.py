"""
companies_company_access.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "companies",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=True),
        sa.Column("website", sa.String(length=2048), nullable=True),
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "length(trim(name)) > 0 AND name = trim(name)",
            name=op.f("ck_companies_name_trimmed"),
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_companies_positive_version")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
    )
    op.create_table(
        "company_access",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
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
            "role IN ('owner', 'admin', 'viewer')",
            name=op.f("ck_company_access_valid_role"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_company_access_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_company_access_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "company_id", "user_id", name=op.f("pk_company_access")
        ),
    )
    op.create_index(
        "ix_access_company_page",
        "company_access",
        [
            "company_id",
            sa.literal_column("created_at DESC"),
            sa.literal_column("user_id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_access_user_page",
        "company_access",
        [
            "user_id",
            sa.literal_column("created_at DESC"),
            sa.literal_column("company_id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "uq_company_owner",
        "company_access",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("role = 'owner'"),
    )


def downgrade():
    op.drop_index(
        "uq_company_owner",
        table_name="company_access",
        postgresql_where=sa.text("role = 'owner'"),
    )
    op.drop_index("ix_access_user_page", table_name="company_access")
    op.drop_index("ix_access_company_page", table_name="company_access")
    op.drop_table("company_access")
    op.drop_table("companies")
