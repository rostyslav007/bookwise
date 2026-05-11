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
from app.services.search_service import ChapterContent, SearchResult, SearchService

mcp = FastMCP(
    name="BooksNavigationMCP",
    instructions=(
        "Search the user's personal technical book library. "
        "Use search_books to find concepts, patterns, and topics in books the user has read. "
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
