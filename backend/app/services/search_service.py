"""Service for semantic search across book chunks using pgvector."""

import base64
import logging
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import fitz
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.book import Book

logger = logging.getLogger(__name__)

_MAX_PAGE_IMAGES = 2
_PAGE_IMAGE_DPI = 100
_MAX_IMAGE_BYTES = 200_000  # ~200KB per image to stay under 1MB total
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # -> BooksNavigationMCP/


def _resolve_book_path(file_path_str: str) -> Path:
    """Resolve a book file path, trying multiple base directories."""
    fp = Path(file_path_str)
    if fp.is_absolute() and fp.exists():
        return fp
    # Try project root (for MCP running from backend/)
    candidate = _PROJECT_ROOT / fp
    if candidate.exists():
        return candidate
    # Try cwd (for Docker where cwd=/app)
    candidate = Path.cwd() / fp
    if candidate.exists():
        return candidate
    return fp
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


class PageImage(BaseModel):
    book_title: str
    page_number: int
    image_base64: str
    media_type: str = "image/png"


class SearchResult(BaseModel):
    results: list[SearchHit]
    images: list[PageImage] = []
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
    images: list[PageImage] | None = None


class SearchService:
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service

    async def extract_page_images(self, hits: list[SearchHit]) -> list[PageImage]:
        """Render referenced PDF pages as base64 JPEG images.

        Prioritizes page_context hits over semantic hits for image selection.
        """
        # Collect pages, prioritizing page_context source
        page_context_pages: dict[str, list[int]] = {}  # book_id -> ordered pages
        semantic_pages: dict[str, list[int]] = {}

        for hit in hits:
            if hit.format != "pdf" or "/books/" not in hit.viewer_url:
                continue
            book_id_str = hit.viewer_url.split("/books/")[1].split("/")[0]
            target = page_context_pages if hit.source == "page_context" else semantic_pages
            target.setdefault(book_id_str, [])
            if hit.page_number not in target[book_id_str]:
                target[book_id_str].append(hit.page_number)

        # Merge: page_context first, then semantic fills remaining slots
        all_book_ids = set(page_context_pages) | set(semantic_pages)
        if not all_book_ids:
            return []

        images: list[PageImage] = []
        for book_id_str in all_book_ids:
            priority_pages = page_context_pages.get(book_id_str, [])
            fallback_pages = [p for p in semantic_pages.get(book_id_str, []) if p not in priority_pages]
            selected_pages = (priority_pages + fallback_pages)[:_MAX_PAGE_IMAGES]

            book = await self._session.get(Book, UUID(book_id_str))
            if not book:
                continue

            file_path = _resolve_book_path(book.file_path)
            if not file_path.exists():
                logger.warning("Book file not found: %s", file_path)
                continue

            try:
                doc = fitz.open(file_path)
                for page_num in selected_pages:
                    if page_num < 1 or page_num > len(doc):
                        continue
                    page = doc[page_num - 1]
                    pix = page.get_pixmap(dpi=_PAGE_IMAGE_DPI)
                    img_bytes = pix.tobytes("jpeg")
                    if len(img_bytes) > _MAX_IMAGE_BYTES:
                        # Re-render at lower DPI if still too large
                        pix = page.get_pixmap(dpi=72)
                        img_bytes = pix.tobytes("jpeg")
                    images.append(PageImage(
                        book_title=book.title,
                        page_number=page_num,
                        image_base64=base64.b64encode(img_bytes).decode(),
                        media_type="image/jpeg",
                    ))
                doc.close()
            except Exception:
                logger.warning("Failed to extract images from %s", file_path)

        return images

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
            viewer_url = (
                f"{settings.frontend_url}/books/{row.book_id}/epub"
                f"?chapterId={row.chapter_id}"
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
        query_embedding = (await self._embedding_service.encode_async([query]))[0]

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

        final_hits = all_hits[:limit]
        page_images = await self.extract_page_images(final_hits)

        return ExplainResult(
            status="ok",
            message=f"Found {len(final_hits)} chunk(s) and {len(page_images)} page image(s) from '{book.title}'.",
            book_title=book.title,
            book_author=book.author,
            results=final_hits,
            images=page_images,
        )
