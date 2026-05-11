"""BooksNavigationMCP - MCP server for searching technical books."""

from pathlib import Path
from uuid import UUID

import fitz
from mcp.server.fastmcp import FastMCP

from app.database import async_session_factory
from app.models.book import Book, BookFormat
from app.models.chapter import Chapter
from app.services.embedding_service import EmbeddingService
from app.services.epub_parser_service import EpubParserService
from app.services.search_service import ChapterContent, ExplainResult, SearchResult, SearchService

mcp = FastMCP(
    name="Bookwise",
    instructions=(
        "Search the user's personal technical book library. "
        "Use search_books to find concepts, patterns, and topics across all books. "
        "Use explain_from_book when the user asks about a concept from a specific book or page. "
        "Results include book title, chapter, page number, and relevant text snippets. "
        "Always search books first before using general knowledge. "
        "If search returns source='not_found', inform the user the answer comes from general knowledge, not their books."
    ),
)

_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


@mcp.tool()
async def search_books(query: str) -> SearchResult:
    """Search the user's book library by concept, pattern, or topic.

    Returns up to 5 results with book title, author, chapter, page number, and a relevant text snippet.
    Use this to find where concepts are discussed in the user's technical books.

    Args:
        query: Natural language search query (e.g., "Observer pattern", "CQRS architecture", "dependency injection")
    """
    embedding_service = _get_embedding_service()
    async with async_session_factory() as session:
        service = SearchService(session, embedding_service)
        return await service.search(query)


_MAX_CONTENT_LENGTH = 10_000


@mcp.tool()
async def get_chapter_content(chapter_id: str) -> ChapterContent:
    """Retrieve the full text content of a specific chapter or section.

    Use a chapter_id from search_books results to get the complete text.

    Args:
        chapter_id: The UUID of the chapter to retrieve (from search_books results)
    """
    async with async_session_factory() as session:
        chapter = await session.get(Chapter, UUID(chapter_id))
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")

        book = await session.get(Book, chapter.book_id)
        if not book:
            raise ValueError(f"Book for chapter {chapter_id} not found")

    file_path = Path(book.file_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if book.format == BookFormat.EPUB.value:
        parser = EpubParserService()
        chapters = parser.extract_toc_and_texts(str(file_path))
        content = ""
        for ch in chapters:
            if ch["title"] == chapter.title:
                content = str(ch.get("text", ""))
                break
        if not content:
            content = "Chapter content not found in EPUB."
    else:
        doc = fitz.open(file_path)
        try:
            content_parts = [
                doc[page_num].get_text()
                for page_num in range(chapter.start_page - 1, min(chapter.end_page, len(doc)))
            ]
        finally:
            doc.close()
        content = "\n".join(content_parts)

    if len(content) > _MAX_CONTENT_LENGTH:
        content = content[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated]"

    return ChapterContent(
        chapter_title=chapter.title,
        book_title=book.title,
        author=book.author,
        start_page=chapter.start_page,
        end_page=chapter.end_page,
        content=content,
    )


@mcp.tool()
async def explain_from_book(
    book_title: str,
    query: str | None = None,
    page_number: int | None = None,
    page_range: int = 5,
    limit: int = 10,
) -> ExplainResult:
    """Retrieve chunks from a specific book to explain a concept the user is reading about.

    Use this when the user asks about a concept from a specific book, optionally at a specific page.
    Supports two retrieval modes (at least one of query or page_number must be provided):
    - Page-based: returns chunks near the given page number (good when the user points to a location)
    - Semantic: finds chunks about the query concept anywhere in the book
    - Both combined: page-context chunks first, then semantic matches fill remaining slots

    If the book title is ambiguous (matches multiple books), returns the list of matches
    so the user can clarify which book they mean.

    Args:
        book_title: Book name to search for (fuzzy matched, e.g., "DDIA" or "Designing Data")
        query: The concept to explain (e.g., "hinted handoff", "B-tree vs LSM-tree")
        page_number: Page where the user is reading (retrieves nearby chunks)
        page_range: Number of pages before/after page_number to include (default: 5)
        limit: Maximum number of chunks to return (default: 10)
    """
    if not query and page_number is None:
        return ExplainResult(
            status="error",
            message="At least one of 'query' or 'page_number' must be provided.",
        )

    embedding_service = _get_embedding_service()
    async with async_session_factory() as session:
        service = SearchService(session, embedding_service)

        matches = await service.fuzzy_match_book(book_title)

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
        all_hits = []
        seen_snippets: set[str] = set()

        # Page-based retrieval
        if page_number is not None:
            page_hits = await service.search_by_page_range(
                book_id=book_id,
                page_start=max(1, page_number - page_range),
                page_end=page_number + page_range,
                limit=limit,
            )
            for hit in page_hits:
                seen_snippets.add(hit.snippet)
                all_hits.append(hit)

        # Semantic retrieval
        if query:
            remaining = limit - len(all_hits)
            if remaining > 0:
                semantic_results = await service.search(
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
