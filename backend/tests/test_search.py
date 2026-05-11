from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookStatus
from app.models.chapter import Chapter
from app.models.chunk import ChunkEmbedding
from app.models.group import Group
from app.services.embedding_service import EmbeddingService


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
async def test_search_endpoint_returns_results(
    client: AsyncClient,
    session: AsyncSession,
    embedding_service: EmbeddingService,
) -> None:
    text = (
        "The Observer pattern defines a one-to-many dependency between objects "
        "so that when one object changes state, all its dependents are notified."
    )
    _, book, chapter, _ = await _create_chunk(session, embedding_service, text)

    response = await client.get("/api/v1/search/", params={"q": "Observer pattern"})

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "library"
    assert len(data["results"]) >= 1
    hit = data["results"][0]
    assert "book_title" in hit
    assert "chapter_title" in hit
    assert "viewer_url" in hit


@pytest.mark.asyncio
async def test_search_endpoint_empty_returns_not_found(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/search/", params={"q": "something"})

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "not_found"
    assert data["results"] == []


@pytest.mark.asyncio
async def test_search_endpoint_missing_query_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/search/")

    assert response.status_code == 422
