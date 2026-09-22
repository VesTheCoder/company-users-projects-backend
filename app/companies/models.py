from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.orm.base import Base
from app.infrastructure.orm.mixins import TimestampMixin, UUIDMixin, VersionMixin


class Company(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0 AND name = trim(name)", name="name_trimmed"
        ),
        CheckConstraint("version > 0", name="positive_version"),
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(5000))
    website: Mapped[str | None] = mapped_column(String(2048))


class CompanyAccess(TimestampMixin, Base):
    __tablename__ = "company_access"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'admin', 'viewer')", name="valid_role"),
        Index(
            "uq_company_owner",
            "company_id",
            unique=True,
            postgresql_where=text("role = 'owner'"),
        ),
        Index(
            "ix_access_company_page",
            "company_id",
            text("created_at DESC"),
            text("user_id DESC"),
        ),
        Index(
            "ix_access_user_page",
            "user_id",
            text("created_at DESC"),
            text("company_id DESC"),
        ),
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16))
