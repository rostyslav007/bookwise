import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse, Response
from starlette.responses import StreamingResponse

from app.config import settings
from app.database import async_session_factory, background_session_factory, get_session
from app.models.book import Book, BookStatus
from app.models.chapter import Chapter
from app.models.chunk import ChunkEmbedding
from app.schemas.book import BookResponse, BookUpdate
from app.schemas.chapter import ChapterResponse
from app.services.book_service import BookService
from app.services.claude_service import ClaudeService
from app.services.embedding_service import EmbeddingService
from app.services.processing_service import ProcessingService
from app.services.progress_tracker import progress_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/books", tags=["books"])

_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service  # noqa: PLW0603
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def _run_processing(book_id: UUID) -> None:
    async with background_session_factory() as session:
        claude_service = ClaudeService(api_key=settings.anthropic_api_key)
        embedding_service = _get_embedding_service()
        processing_service = ProcessingService(
            session,
            claude_service,
            tracker=progress_tracker,
            embedding_service=embedding_service,
        )
        await processing_service.process_book(book_id)


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def upload_book(
    background_tasks: BackgroundTasks,
    group_id: UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> BookResponse:
    service = BookService(session)
    book = await service.upload_and_create(group_id, file)
    background_tasks.add_task(_run_processing, book.id)
    return BookResponse.model_validate(book)


@router.get("/{book_id}/progress")
async def book_progress_sse(book_id: UUID) -> StreamingResponse:
    """SSE endpoint for real-time processing progress."""
    queue = progress_tracker.subscribe(book_id)

    async def event_stream():
        try:
            while True:
                step = await queue.get()
                yield f"data: {step}\n\n"
                if step == "__DONE__":
                    break
        finally:
            progress_tracker.unsubscribe(book_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/", response_model=list[BookResponse])
async def list_books(
    group_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[BookResponse]:
    service = BookService(session)
    books = await service.get_all(group_id)
    return [BookResponse.model_validate(b) for b in books]


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> BookResponse:
    service = BookService(session)
    book = await service.get_by_id(book_id)
    return BookResponse.model_validate(book)


@router.patch("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: UUID,
    data: BookUpdate,
    session: AsyncSession = Depends(get_session),
) -> BookResponse:
    service = BookService(session)
    book = await service.update_title(book_id, data.title)
    return BookResponse.model_validate(book)


@router.get("/{book_id}/pdf")
async def serve_book_pdf(
    book_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    service = BookService(session)
    book = await service.get_by_id(book_id)

    file_path = Path(book.file_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"{book.title}.pdf",
    )


@router.get("/{book_id}/file")
async def serve_book_file(
    book_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    service = BookService(session)
    book = await service.get_by_id(book_id)

    file_path = Path(book.file_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime_type = "application/pdf" if book.format == "pdf" else "application/epub+zip"
    extension = ".pdf" if book.format == "pdf" else ".epub"

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=f"{book.title}{extension}",
    )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = BookService(session)
    await service.delete(book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{book_id}/chapters", response_model=list[ChapterResponse])
async def get_book_chapters(
    book_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ChapterResponse]:
    service = BookService(session)
    await service.get_by_id(book_id)  # raises 404 if not found

    result = await session.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.order)
    )
    chapters = list(result.scalars().all())

    return _build_chapter_tree(chapters)


@router.post("/{book_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_book(
    book_id: UUID,
    background_tasks: BackgroundTasks,
    strategy: str = "headings",
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    from app.services.processing_service import ChunkingStrategy
    try:
        chunking_strategy = ChunkingStrategy(strategy)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy. Use: {', '.join(s.value for s in ChunkingStrategy)}")
    service = BookService(session)
    book = await service.get_by_id(book_id)
    book.status = BookStatus.PROCESSING.value
    await session.commit()
    background_tasks.add_task(_run_reindex, book_id, chunking_strategy.value)
    return {"status": "reindexing", "strategy": strategy}


async def _run_reindex(book_id: UUID, strategy: str = "headings") -> None:
    from app.services.processing_service import ChunkingStrategy
    chunking = ChunkingStrategy(strategy) if isinstance(strategy, str) else strategy
    try:
        async with background_session_factory() as session:
            # Delete existing chunks and chapters
            await session.execute(
                delete(ChunkEmbedding).where(ChunkEmbedding.book_id == book_id)
            )
            await session.execute(
                delete(Chapter).where(Chapter.book_id == book_id)
            )
            await session.commit()

            book = await session.get(Book, book_id)
            if not book:
                return

            embedding_service = _get_embedding_service()
            processing_service = ProcessingService(
                session,
                claude_service=ClaudeService(api_key=settings.anthropic_api_key),
                tracker=progress_tracker,
                embedding_service=embedding_service,
            )
            if book.format == "epub":
                from app.services.epub_parser_service import EpubParserService
                parser = EpubParserService()
                epub_chapters = parser.extract_toc_and_texts(book.file_path)
                # Rebuild chapter structure from EPUB TOC
                structure = [
                    {"title": ch["title"], "start_page": int(ch["order"]) + 1,
                     "end_page": int(ch["order"]) + 1, "children": []}
                    for ch in epub_chapters
                ]
                await processing_service._save_chapters(book_id, structure)
                await session.flush()
                await processing_service._embed_epub_chapters(book_id, epub_chapters, chunking)
            else:
                import fitz
                doc = fitz.open(book.file_path)
                toc = doc.get_toc()
                total_pages = len(doc)
                doc.close()
                # Rebuild hierarchical chapter structure from PyMuPDF TOC
                structure = ProcessingService._toc_to_structure(toc, total_pages)
                await processing_service._save_chapters(book_id, structure)
                await session.flush()
                await processing_service._embed_chapters(book_id, book.file_path, chunking)

            book.status = BookStatus.READY.value
            await session.commit()
            processing_service._emit_complete(book_id, "Done")
    except Exception:
        logger.exception("Failed to reindex book %s", book_id)
        async with background_session_factory() as session:
            book = await session.get(Book, book_id)
            if book:
                book.status = BookStatus.READY.value
                await session.commit()
        progress_tracker.complete(book_id)


def _build_chapter_tree(chapters: list[Chapter]) -> list[ChapterResponse]:
    response_map: dict[UUID, ChapterResponse] = {}
    roots: list[ChapterResponse] = []

    for chapter in chapters:
        response_map[chapter.id] = ChapterResponse.model_validate(chapter)

    for chapter in chapters:
        node = response_map[chapter.id]
        if chapter.parent_id and chapter.parent_id in response_map:
            response_map[chapter.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots
