from uuid import uuid4

import fitz
import pytest

from app.models.book import Book, BookStatus
from app.models.chapter import Chapter
from app.models.chunk import ChunkEmbedding
from app.services.processing_service import ProcessingService
from sqlalchemy import select


class _StubEmbeddingService:
    async def encode_async(self, texts):
        return [[0.0] * 384 for _ in texts]


@pytest.fixture
def two_chapter_pdf_path(tmp_path) -> str:
    doc = fitz.open()
    for page_index in range(2):
        page = doc.new_page()
        for line in range(20):
            page.insert_text(
                (72, 72 + line * 14),
                f"Chapter {page_index} line {line}: architecture content for chunking.",
            )
    path = tmp_path / "two_chapters.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


async def test_embed_chapters_stores_chunks(session, sample_group, two_chapter_pdf_path):
    book = Book(
        group_id=sample_group.id,
        title="Two Chapter Book",
        file_path=two_chapter_pdf_path,
        status=BookStatus.PROCESSING.value,
    )
    session.add(book)
    await session.flush()
    for order, title in enumerate(["Chapter One", "Chapter Two"]):
        session.add(
            Chapter(
                book_id=book.id,
                title=title,
                start_page=order + 1,
                end_page=order + 1,
                order=order,
                level=0,
            )
        )
    await session.commit()

    service = ProcessingService(
        session, claude_service=None, embedding_service=_StubEmbeddingService()
    )

    await service._embed_chapters(book.id, book.file_path)

    result = await session.execute(
        select(ChunkEmbedding).where(ChunkEmbedding.book_id == book.id)
    )
    assert len(result.scalars().all()) > 0
