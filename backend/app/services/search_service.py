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


class BookMatch(BaseModel):
    title: str
    author: str | None
    book_id: str


class ExplainResult(BaseModel):
    status: str  # "ok", "ambiguous", "not_found"
    message: str
    book_title: str | None = None
    book_author: str | None = None
    matches: list[BookMatch] | None = None
    results: list[SearchHit] | None = None


class SearchService:
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service

    async def fuzzy_match_book(self, book_title: str) -> list[BookMatch]:
        """Find books matching a (potentially vague) title using case-insensitive containment."""
        sql = text("""
            SELECT id, title, author FROM books
            WHERE LOWER(title) LIKE '%' || LOWER(:query) || '%'
            ORDER BY title
        """)
        result = await self._session.execute(sql, {"query": book_title})
        return [
            BookMatch(title=row.title, author=row.author, book_id=str(row.id))
            for row in result.fetchall()
        ]

    async def search_by_page_range(
        self,
        book_id: UUID,
        page_start: int,
        page_end: int,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Retrieve chunks within a page range for a specific book."""
        sql = text("""
            SELECT
                ce.content, ce.page_number, ce.chapter_id, ce.book_id,
                c.title AS chapter_title,
                b.title AS book_title, b.author, b.format
            FROM chunk_embeddings ce
            JOIN chapters c ON ce.chapter_id = c.id
            JOIN books b ON ce.book_id = b.id
            WHERE ce.book_id = :book_id
              AND ce.page_number BETWEEN :page_start AND :page_end
            ORDER BY ce.page_number
            LIMIT :limit
        """)
        result = await self._session.execute(sql, {
            "book_id": str(book_id),
            "page_start": page_start,
            "page_end": page_end,
            "limit": limit,
        })
        return [self._row_to_hit(row, source="page_context") for row in result.fetchall()]

    def _row_to_hit(self, row, source: str = "semantic", relevance_score: float = 0.0) -> SearchHit:
        """Convert a DB row to a SearchHit."""
        if row.format == "epub":
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
        return SearchHit(
            book_title=row.book_title,
            author=row.author,
            chapter_title=row.chapter_title,
            chapter_id=str(row.chapter_id),
            page_number=row.page_number,
            snippet=row.content[:500],
            relevance_score=round(relevance_score, 4),
            viewer_url=viewer_url,
            format=row.format,
            source=source,
        )

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

        hits = [
            self._row_to_hit(row, source="semantic", relevance_score=float(row.relevance_score))
            for row in rows
        ]

        return SearchResult(
            results=hits,
            source="library",
            message=f"Found {len(hits)} result(s) in your book library.",
        )

    async def explain_from_book(
        self,
        book_title: str,
        query: str | None = None,
        page_number: int | None = None,
        page_range: int = 5,
        limit: int = 10,
    ) -> ExplainResult:
        """Fuzzy match a book and retrieve chunks by page range, semantic search, or both."""
        if not query and page_number is None:
            return ExplainResult(
                status="error",
                message="At least one of 'query' or 'page_number' must be provided.",
            )

        matches = await self.fuzzy_match_book(book_title)

        if not matches:
            return ExplainResult(
                status="not_found",
                message=f"No books matching '{book_title}' found in your library.",
            )

        if len(matches) > 1:
            return ExplainResult(
                status="ambiguous",
                message=f"Multiple books matched '{book_title}'. Specify which one.",
                matches=matches,
            )

        book = matches[0]
        book_id = UUID(book.book_id)
        all_hits: list[SearchHit] = []
        seen_snippets: set[str] = set()

        if page_number is not None:
            page_hits = await self.search_by_page_range(
                book_id=book_id,
                page_start=max(1, page_number - page_range),
                page_end=page_number + page_range,
                limit=limit,
            )
            for hit in page_hits:
                seen_snippets.add(hit.snippet)
                all_hits.append(hit)

        if query:
            remaining = limit - len(all_hits)
            if remaining > 0:
                semantic_results = await self.search(
                    query, limit=remaining, book_id=book_id
                )
                for hit in semantic_results.results:
                    if hit.snippet not in seen_snippets:
                        hit.source = "semantic"
                        seen_snippets.add(hit.snippet)
                        all_hits.append(hit)

        return ExplainResult(
            status="ok",
            message=f"Found {len(all_hits)} chunk(s) from '{book.title}'.",
            book_title=book.title,
            book_author=book.author,
            results=all_hits[:limit],
        )
