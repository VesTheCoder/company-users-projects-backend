from datetime import date
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.orm.base import Base
from app.infrastructure.orm.mixins import TimestampMixin, UUIDMixin, VersionMixin


class Employee(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "length(trim(full_name)) > 0 AND full_name = trim(full_name)",
            name="name_trimmed",
        ),
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint(
            "status IN ('active','leave','terminated')", name="valid_status"
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="date_order"
        ),
        CheckConstraint(
            "(status = 'terminated') = (end_date IS NOT NULL)", name="termination_date"
        ),
        CheckConstraint(
            "work_phone IS NULL OR work_phone ~ '^\\+[1-9][0-9]{1,14}$'",
            name="phone_format",
        ),
        UniqueConstraint("id", "company_id", name="uq_employee_id_company"),
        Index(
            "uq_employee_company_email",
            "company_id",
            "work_email_normalized",
            unique=True,
            postgresql_where=text("work_email_normalized IS NOT NULL"),
        ),
        Index(
            "ix_employee_page", "company_id", text("created_at DESC"), text("id DESC")
        ),
        Index(
            "ix_employee_status_page",
            "company_id",
            "status",
            text("created_at DESC"),
            text("id DESC"),
        ),
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    full_name: Mapped[str] = mapped_column(String(200))
    work_email: Mapped[str | None] = mapped_column(String(254))
    work_email_normalized: Mapped[str | None] = mapped_column(String(254))
    work_phone: Mapped[str | None] = mapped_column(String(16))
    job_title: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16))
    start_date: Mapped[date]
    end_date: Mapped[date | None]
