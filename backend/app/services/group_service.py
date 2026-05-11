from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.schemas.group import GroupCreate, GroupUpdate


class GroupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: GroupCreate) -> Group:
        group = Group(name=data.name)
        self._session.add(group)
        await self._session.commit()
        await self._session.refresh(group)
        return group

    async def get_all(self) -> list[Group]:
        result = await self._session.execute(select(Group))
        return list(result.scalars().all())

    async def update(self, group_id: UUID, data: GroupUpdate) -> Group:
        group = await self._session.get(Group, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
            )
        group.name = data.name
        await self._session.commit()
        await self._session.refresh(group)
        return group

    async def delete(self, group_id: UUID) -> None:
        group = await self._session.get(Group, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
            )

        from pathlib import Path

        from app.models.book import Book

        result = await self._session.execute(select(Book).where(Book.group_id == group_id))
        books = list(result.scalars().all())
        for book in books:
            Path(book.file_path).unlink(missing_ok=True)

        await self._session.delete(group)
        await self._session.commit()
