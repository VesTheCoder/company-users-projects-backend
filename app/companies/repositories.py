from sqlalchemy import select

from app.auth.models import User
from app.companies.models import Company, CompanyAccess
from app.exceptions.base import AppError
from app.utils.pagination import page_query


class CompanyRepository:
    def __init__(self, session):
        self.session = session

    async def accessible(self, company_id, user_id, *, lock=False):
        query = select(Company).where(
            Company.id == company_id,
            select(CompanyAccess.company_id)
            .where(
                CompanyAccess.company_id == company_id, CompanyAccess.user_id == user_id
            )
            .exists(),
        )
        if lock:
            query = query.with_for_update(of=Company)
        company = await self.session.scalar(query)
        if company is None:
            raise AppError(404, "resource_not_found", "Resource not found.")
        access = await self.session.get(
            CompanyAccess, (company_id, user_id), populate_existing=True
        )
        if access is None:
            raise AppError(404, "resource_not_found", "Resource not found.")
        return company, access.role

    async def page(self, user_id, role, after, limit):
        query = (
            select(Company, CompanyAccess)
            .join(CompanyAccess)
            .where(CompanyAccess.user_id == user_id)
        )
        if role:
            query = query.where(CompanyAccess.role == role)
        query = page_query(
            query, CompanyAccess.created_at, CompanyAccess.company_id, after, limit
        )
        return (await self.session.execute(query)).all()


class AccessRepository:
    def __init__(self, session):
        self.session = session

    async def member(self, company_id, user_id, *, lock=False):
        query = select(CompanyAccess).where(
            CompanyAccess.company_id == company_id, CompanyAccess.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def read(self, company_id, user_id):
        return (
            await self.session.execute(
                select(CompanyAccess, User)
                .join(User)
                .where(
                    CompanyAccess.company_id == company_id,
                    CompanyAccess.user_id == user_id,
                )
            )
        ).one()

    async def page(self, company_id, role, after, limit):
        query = (
            select(CompanyAccess, User)
            .join(User)
            .where(CompanyAccess.company_id == company_id)
        )
        if role:
            query = query.where(CompanyAccess.role == role)
        return (
            await self.session.execute(
                page_query(
                    query, CompanyAccess.created_at, CompanyAccess.user_id, after, limit
                )
            )
        ).all()
