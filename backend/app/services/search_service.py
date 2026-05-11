"""Service for semantic search across book chunks using pgvector."""

from urllib.parse import quote_plus
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.embedding_service import EmbeddingService


class ChapterContent(BaseModel):
    chapter_title: str
    book_title: str
    author: str | None
    start_page: int
    end_page: int
    content: str
    source: str = "library"


class SearchHit(BaseModel):
    book_title: str
    author: str | None
    chapter_title: str
    chapter_id: str
    page_number: int
    snippet: str
    relevance_score: float
    viewer_url: str
    format: str
    source: str = "library"


class SearchResult(BaseModel):
    results: list[SearchHit]
    source: str  # "library" or "not_found"
    message: str


class SearchService:
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service

    async def search(
        self,
        query: str,
        limit: int = 5,
        group_id: UUID | None = None,
        book_id: UUID | None = None,
    ) -> SearchResult:
        """Search book chunks by semantic similarity using pgvector cosine distance."""
        query_embedding = self._embedding_service.encode([query])[0]

        where_clauses = ""
        params: dict[str, str | int] = {"embedding": str(query_embedding), "limit": limit}

        if book_id:
            where_clauses += " AND ce.book_id = :book_id"
            params["book_id"] = str(book_id)
        elif group_id:
            where_clauses += " AND b.group_id = :group_id"
            params["group_id"] = str(group_id)

        sql = text(f"""
            SELECT
                ce.content,
                ce.page_number,
                ce.chapter_id,
                ce.book_id,
                c.title AS chapter_title,
                b.title AS book_title,
                b.author,
                b.format,
                1 - (ce.embedding <=> CAST(:embedding AS vector)) AS relevance_score
            FROM chunk_embeddings ce
            JOIN chapters c ON ce.chapter_id = c.id
            JOIN books b ON ce.book_id = b.id
            WHERE 1=1 {where_clauses}
            ORDER BY ce.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        result = await self._session.execute(sql, params)
        rows = result.fetchall()

        if not rows:
            return SearchResult(
                results=[],
                source="not_found",
                message="No matches found in your book library.",
            )

        hits = []
        for row in rows:
            if row.format == "epub":
                # page_number stores chapter order (1-indexed) for EPUBs
                chapter_index = row.page_number - 1
                viewer_url = (
                    f"{settings.frontend_url}/books/{row.book_id}/epub"
                    f"?chapter={chapter_index}"
                )
            else:
                viewer_url = (
                    f"{settings.frontend_url}/books/{row.book_id}/view"
                    f"?page={row.page_number}"
                    f"&highlight={quote_plus(str(row.content)[:80])}"
                )
            hits.append(
                SearchHit(
                    book_title=row.book_title,
                    author=row.author,
                    chapter_title=row.chapter_title,
                    chapter_id=str(row.chapter_id),
                    page_number=row.page_number,
                    snippet=row.content[:500],
                    relevance_score=round(float(row.relevance_score), 4),
                    viewer_url=viewer_url,
                    format=row.format,
                )
            )

        return SearchResult(
            results=hits,
            source="library",
            message=f"Found {len(hits)} result(s) in your book library.",
        )
