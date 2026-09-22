"""
employees_projects_assignments.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employees",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("work_email", sa.String(length=254), nullable=True),
        sa.Column("work_email_normalized", sa.String(length=254), nullable=True),
        sa.Column("work_phone", sa.String(length=16), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
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
            "(status = 'terminated') = (end_date IS NOT NULL)",
            name=op.f("ck_employees_termination_date"),
        ),
        sa.CheckConstraint(
            "status IN ('active','leave','terminated')",
            name=op.f("ck_employees_valid_status"),
        ),
        sa.CheckConstraint(
            "work_phone IS NULL OR work_phone ~ '^\\+[1-9][0-9]{1,14}$'",
            name=op.f("ck_employees_phone_format"),
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_employees_date_order"),
        ),
        sa.CheckConstraint(
            "length(trim(full_name)) > 0 AND full_name = trim(full_name)",
            name=op.f("ck_employees_name_trimmed"),
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_employees_positive_version")),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_employees_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employees")),
        sa.UniqueConstraint("id", "company_id", name="uq_employee_id_company"),
    )
    op.create_index(
        "ix_employee_page",
        "employees",
        [
            "company_id",
            sa.literal_column("created_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_employee_status_page",
        "employees",
        [
            "company_id",
            "status",
            sa.literal_column("created_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "uq_employee_company_email",
        "employees",
        ["company_id", "work_email_normalized"],
        unique=True,
        postgresql_where=sa.text("work_email_normalized IS NOT NULL"),
    )
    op.create_table(
        "projects",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
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
            "status IN ('planned','active','completed','cancelled')",
            name=op.f("ck_projects_valid_status"),
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR (start_date IS NOT NULL AND end_date >= start_date)",
            name=op.f("ck_projects_date_order"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0 AND name = trim(name)",
            name=op.f("ck_projects_name_trimmed"),
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_projects_positive_version")),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_projects_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("id", "company_id", name="uq_project_id_company"),
    )
    op.create_index(
        "ix_project_page",
        "projects",
        [
            "company_id",
            sa.literal_column("created_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_project_status_page",
        "projects",
        [
            "company_id",
            "status",
            sa.literal_column("created_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )
    op.create_table(
        "project_employees",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
            name=op.f("fk_project_employees_assigned_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id", "company_id"],
            ["employees.id", "employees.company_id"],
            name=op.f("fk_project_employees_employee_id_employees"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "company_id"],
            ["projects.id", "projects.company_id"],
            name=op.f("fk_project_employees_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "company_id", "project_id", "employee_id", name=op.f("pk_project_employees")
        ),
    )
    op.create_index(
        "ix_assignment_employee",
        "project_employees",
        ["company_id", "employee_id", "project_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignment_page",
        "project_employees",
        [
            "company_id",
            "project_id",
            sa.literal_column("assigned_at DESC"),
            sa.literal_column("employee_id DESC"),
        ],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_assignment_page", table_name="project_employees")
    op.drop_index("ix_assignment_employee", table_name="project_employees")
    op.drop_table("project_employees")
    op.drop_index("ix_project_status_page", table_name="projects")
    op.drop_index("ix_project_page", table_name="projects")
    op.drop_table("projects")
    op.drop_index(
        "uq_employee_company_email",
        table_name="employees",
        postgresql_where=sa.text("work_email_normalized IS NOT NULL"),
    )
    op.drop_index("ix_employee_status_page", table_name="employees")
    op.drop_index("ix_employee_page", table_name="employees")
    op.drop_table("employees")
