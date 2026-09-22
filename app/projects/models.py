from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.orm.base import Base
from app.infrastructure.orm.mixins import TimestampMixin, UUIDMixin, VersionMixin


class Project(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0 AND name = trim(name)", name="name_trimmed"
        ),
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint(
            "status IN ('planned','active','completed','cancelled')",
            name="valid_status",
        ),
        CheckConstraint(
            "end_date IS NULL OR (start_date IS NOT NULL AND end_date >= start_date)",
            name="date_order",
        ),
        UniqueConstraint("id", "company_id", name="uq_project_id_company"),
        Index(
            "ix_project_page", "company_id", text("created_at DESC"), text("id DESC")
        ),
        Index(
            "ix_project_status_page",
            "company_id",
            "status",
            text("created_at DESC"),
            text("id DESC"),
        ),
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(5000))
    status: Mapped[str] = mapped_column(String(16))
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]


class ProjectEmployee(Base):
    __tablename__ = "project_employees"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "company_id"],
            ["projects.id", "projects.company_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["employee_id", "company_id"],
            ["employees.id", "employees.company_id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_assignment_page",
            "company_id",
            "project_id",
            text("assigned_at DESC"),
            text("employee_id DESC"),
        ),
        Index("ix_assignment_employee", "company_id", "employee_id", "project_id"),
    )
    company_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    employee_id: Mapped[UUID] = mapped_column(primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
