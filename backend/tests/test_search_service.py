from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookStatus
from app.models.chapter import Chapter
from app.models.chunk import ChunkEmbedding
from app.models.group import Group
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


@pytest.fixture(scope="session")
def embedding_service() -> EmbeddingService:
    return EmbeddingService()


async def _create_chunk(
    session: AsyncSession,
    embedding_service: EmbeddingService,
    text: str,
    *,
    book_title: str = "Design Patterns",
    author: str = "GoF",
    chapter_title: str = "Observer Pattern",
    page_number: int = 5,
) -> tuple[Group, Book, Chapter, ChunkEmbedding]:
    """Insert a group, book, chapter, and chunk with a real embedding vector."""
    group = Group(name=f"test-group-{uuid4().hex[:8]}")
    session.add(group)
    await session.flush()

    book = Book(
        group_id=group.id,
        title=book_title,
        author=author,
        file_path="data/books/test.pdf",
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.flush()

    chapter = Chapter(
        book_id=book.id,
        title=chapter_title,
        level=0,
        order=0,
        start_page=1,
        end_page=10,
    )
    session.add(chapter)
    await session.flush()

    embedding = embedding_service.encode([text])[0]

    chunk = ChunkEmbedding(
        chapter_id=chapter.id,
        book_id=book.id,
        content=text,
        page_number=page_number,
        embedding=embedding,
    )
    session.add(chunk)
    await session.commit()

    return group, book, chapter, chunk


@pytest.mark.asyncio
async def test_search_returns_results(session: AsyncSession, embedding_service: EmbeddingService) -> None:
    test_text = (
        "The Observer pattern defines a one-to-many dependency between objects "
        "so that when one object changes state, all its dependents are notified."
    )
    _, book, chapter, chunk = await _create_chunk(session, embedding_service, test_text)

    service = SearchService(session, embedding_service)
    result = await service.search("observer pattern notification")

    assert result.source == "library"
    assert len(result.results) >= 1

    hit = result.results[0]
    assert hit.book_title == book.title
    assert hit.chapter_title == chapter.title
    assert hit.page_number == chunk.page_number
    assert hit.snippet in test_text
    assert hit.source == "library"
    assert hit.relevance_score > 0


@pytest.mark.asyncio
async def test_search_no_matches_returns_not_found(session: AsyncSession, embedding_service: EmbeddingService) -> None:
    service = SearchService(session, embedding_service)
    result = await service.search("something completely irrelevant")

    assert result.source == "not_found"
    assert result.results == []


@pytest.mark.asyncio
async def test_search_limits_results(session: AsyncSession, embedding_service: EmbeddingService) -> None:
    texts = [
        "The Strategy pattern defines a family of algorithms and makes them interchangeable.",
        "The Factory Method pattern provides an interface for creating objects in a superclass.",
        "The Singleton pattern ensures a class has only one instance and provides a global point of access.",
    ]
    for i, text in enumerate(texts):
        await _create_chunk(
            session,
            embedding_service,
            text,
            book_title=f"Patterns Book {i}",
            chapter_title=f"Chapter {i}",
            page_number=i + 1,
        )

    service = SearchService(session, embedding_service)
    result = await service.search("design pattern", limit=2)

    assert len(result.results) == 2
    assert result.source == "library"
