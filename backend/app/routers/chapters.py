from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.database import get_session
from app.schemas.chapter import ChapterCreate, ChapterMergeRequest, ChapterResponse, ChapterUpdate
from app.services.chapter_service import ChapterService

router = APIRouter(prefix="/api/v1", tags=["chapters"])


@router.post("/books/{book_id}/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    book_id: UUID,
    data: ChapterCreate,
    session: AsyncSession = Depends(get_session),
) -> ChapterResponse:
    service = ChapterService(session)
    chapter = await service.create(book_id, data)
    return ChapterResponse.model_validate(chapter)


@router.put("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: UUID,
    data: ChapterUpdate,
    session: AsyncSession = Depends(get_session),
) -> ChapterResponse:
    service = ChapterService(session)
    chapter = await service.update(chapter_id, data)
    return ChapterResponse.model_validate(chapter)


@router.delete("/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    chapter_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = ChapterService(session)
    await service.delete(chapter_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chapters/merge", response_model=ChapterResponse)
async def merge_chapters(
    data: ChapterMergeRequest,
    session: AsyncSession = Depends(get_session),
) -> ChapterResponse:
    service = ChapterService(session)
    chapter = await service.merge(data.chapter_ids)
    return ChapterResponse.model_validate(chapter)
