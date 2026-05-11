from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func as sa_func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.models.chunk import ChunkEmbedding
from app.schemas.chapter import ChapterCreate, ChapterUpdate


class ChapterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def update(self, chapter_id: UUID, data: ChapterUpdate) -> Chapter:
        chapter = await self._session.get(Chapter, chapter_id)
        if not chapter:
            raise HTTPException(404, "Chapter not found")

        if data.title is not None:
            chapter.title = data.title
        if data.start_page is not None:
            chapter.start_page = data.start_page
        if data.end_page is not None:
            chapter.end_page = data.end_page

        await self._session.commit()
        await self._session.refresh(chapter)
        return chapter

    async def create(self, book_id: UUID, data: ChapterCreate) -> Chapter:
        level = 0
        if data.parent_id:
            parent = await self._session.get(Chapter, data.parent_id)
            if not parent:
                raise HTTPException(404, "Parent chapter not found")
            level = parent.level + 1

        stmt = select(sa_func.coalesce(sa_func.max(Chapter.order), -1)).where(
            Chapter.book_id == book_id,
            Chapter.parent_id == data.parent_id,
        )
        result = await self._session.execute(stmt)
        max_order: int = result.scalar() or -1

        chapter = Chapter(
            book_id=book_id,
            parent_id=data.parent_id,
            title=data.title,
            level=level,
            order=max_order + 1,
            start_page=data.start_page,
            end_page=data.end_page,
        )
        self._session.add(chapter)
        await self._session.commit()
        await self._session.refresh(chapter)
        return chapter

    async def delete(self, chapter_id: UUID) -> None:
        chapter = await self._session.get(Chapter, chapter_id)
        if not chapter:
            raise HTTPException(404, "Chapter not found")

        await self._session.execute(
            delete(ChunkEmbedding).where(ChunkEmbedding.chapter_id == chapter_id)
        )
        await self._session.delete(chapter)
        await self._session.commit()

    async def merge(self, chapter_ids: list[UUID]) -> Chapter:
        if len(chapter_ids) != 2:
            raise HTTPException(400, "Exactly 2 chapter IDs required")

        chapters: list[Chapter] = []
        for cid in chapter_ids:
            chapter = await self._session.get(Chapter, cid)
            if not chapter:
                raise HTTPException(404, f"Chapter {cid} not found")
            chapters.append(chapter)

        if chapters[0].parent_id != chapters[1].parent_id:
            raise HTTPException(400, "Chapters must have the same parent")
        if chapters[0].book_id != chapters[1].book_id:
            raise HTTPException(400, "Chapters must belong to the same book")

        chapters.sort(key=lambda c: c.order)
        first, second = chapters

        first.title = f"{first.title} / {second.title}"
        first.start_page = min(first.start_page, second.start_page)
        first.end_page = max(first.end_page, second.end_page)

        # Re-parent children of second chapter to first
        await self._session.execute(
            sa_update(Chapter).where(Chapter.parent_id == second.id).values(parent_id=first.id)
        )

        # Delete chunks belonging to second chapter
        await self._session.execute(
            delete(ChunkEmbedding).where(ChunkEmbedding.chapter_id == second.id)
        )
        await self._session.delete(second)

        await self._session.commit()
        await self._session.refresh(first)
        return first
