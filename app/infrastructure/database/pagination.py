"""Shared pagination helper for SQLAlchemy async repositories.

Usage:
    stmt = select(Model).where(...).order_by(Model.created_at.desc())
    rows, total = await paginate(session, stmt, limit=limit, offset=offset)
"""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    stmt: Select,
    *,
    limit: int,
    offset: int,
) -> tuple[list, int]:
    """Execute a COUNT and a paged SELECT for the same base query.

    The ORDER BY clause is stripped before counting so the DB doesn't sort
    a potentially large result set just to count it.
    """
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()
    result = await session.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all()), total
