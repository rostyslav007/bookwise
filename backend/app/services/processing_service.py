from __future__ import annotations

import enum
import logging
from typing import TYPE_CHECKING
from uuid import UUID

import fitz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookFormat, BookStatus
from app.models.chapter import Chapter
from app.models.chunk import ChunkEmbedding
from app.services.claude_service import ClaudeService
from app.services.epub_parser_service import EpubParserService
from app.services.progress_tracker import ProgressTracker

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, enum.Enum):
    HEADINGS = "headings"
    FIXED = "fixed"


_MAX_SAMPLE_PAGES = 50
_MAX_TEXT_PER_PAGE = 2000
_CHUNK_SIZE = 2000
_CHUNK_OVERLAP = 400
_MAX_CHUNK_SIZE = 4000  # heading-based sections larger than this get sub-split
_MIN_CHUNK_SIZE = 200   # chunks smaller than this get merged with the next one


class ProcessingService:
    def __init__(
        self,
        session: AsyncSession,
        claude_service: ClaudeService,
        tracker: ProgressTracker | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session = session
        self._claude_service = claude_service
        self._tracker = tracker
        self._embedding_service = embedding_service

    async def process_book(self, book_id: UUID) -> None:
        """Main pipeline: extract metadata, TOC, AI enrichment, save chapters."""
        book = await self._session.get(Book, book_id)
        if not book:
            logger.warning("Book %s not found, skipping processing", book_id)
            return

        try:
            if book.format == BookFormat.EPUB.value:
                await self._process_epub(book)
            else:
                await self._process_pdf(book)

            book.status = BookStatus.READY.value
            await self._session.commit()
            self._emit_complete(book_id, "Done")

        except Exception:
            logger.exception("Failed to process book %s", book_id)
            book.status = BookStatus.ERROR.value
            await self._session.commit()
            self._emit_complete(book_id, "Error")
            raise

    async def _process_pdf(self, book: Book) -> None:
        """Process a PDF book through the full pipeline."""
        self._emit(book.id, "Extracting metadata...")
        doc = fitz.open(book.file_path)
        self._extract_metadata(book, doc)

        self._emit(book.id, "Extracting chapters...")
        toc = doc.get_toc()
        page_samples = self._extract_page_samples(doc)
        doc.close()

        structure = await self._generate_structure(book.id, book.title, book.page_count or 0, toc, page_samples)

        self._emit(book.id, "Saving chapters...")
        await self._save_chapters(book.id, structure)

        if self._embedding_service:
            await self._embed_chapters(book.id, book.file_path)

    async def _process_epub(self, book: Book) -> None:
        """Process an EPUB book through the full pipeline."""
        parser = EpubParserService()

        self._emit(book.id, "Extracting metadata...")
        metadata = parser.extract_metadata(book.file_path)
        if metadata.get("title"):
            book.title = metadata["title"].replace("\x00", "").strip()
        if metadata.get("author"):
            book.author = metadata["author"].replace("\x00", "").strip()

        self._emit(book.id, "Extracting chapters...")
        chapters = parser.extract_toc_and_texts(book.file_path)
        book.page_count = len(chapters)

        structure = [
            {
                "title": ch["title"],
                "start_page": int(ch["order"]) + 1,
                "end_page": int(ch["order"]) + 1,
                "children": [],
            }
            for ch in chapters
        ]

        self._emit(book.id, "Saving chapters...")
        await self._save_chapters(book.id, structure)

        if self._embedding_service:
            await self._embed_epub_chapters(book.id, chapters)

    async def _embed_epub_chapters(
        self,
        book_id: UUID,
        chapters: list[dict[str, str | int]],
        strategy: ChunkingStrategy = ChunkingStrategy.HEADINGS,
    ) -> None:
        """Chunk and embed EPUB chapter texts in batches."""
        # Phase 1: Chunk all chapters and collect metadata
        self._emit(book_id, "Chunking text...")
        chunk_records: list[tuple[str, UUID, int]] = []  # (text, chapter_id, page_number)
        all_texts: list[str] = []

        for idx, ch in enumerate(chapters):
            html = str(ch.get("html", ""))
            text = str(ch.get("text", ""))
            if not text.strip():
                continue

            if strategy == ChunkingStrategy.HEADINGS and html:
                chunks = self._chunk_epub_html_by_headings(html)
                if not chunks:
                    chunks = self._chunk_text(text)
            else:
                chunks = self._chunk_text(text)
            if not chunks:
                continue

            result = await self._session.execute(
                select(Chapter).where(
                    Chapter.book_id == book_id,
                    Chapter.order == idx,
                    Chapter.parent_id.is_(None),
                )
            )
            chapter_record = result.scalar_one_or_none()
            if not chapter_record:
                continue

            page_number = int(ch.get("order", 0)) + 1
            for chunk_text in chunks:
                all_texts.append(chunk_text)
                chunk_records.append((chunk_text, chapter_record.id, page_number))

        if not all_texts:
            return

        # Phase 2: Encode all chunks in batches
        batch_size = 64
        all_embeddings: list[list[float]] = []
        total_chunks = len(all_texts)
        for i in range(0, total_chunks, batch_size):
            batch = all_texts[i : i + batch_size]
            self._emit(book_id, f"Encoding embeddings... ({min(i + batch_size, total_chunks)}/{total_chunks})")
            embeddings = await self._embedding_service.encode_async(batch)
            all_embeddings.extend(embeddings)

        # Phase 3: Insert all chunk embeddings
        self._emit(book_id, "Saving to database...")
        for (chunk_text, chapter_id, page_number), embedding in zip(chunk_records, all_embeddings):
            self._session.add(
                ChunkEmbedding(
                    chapter_id=chapter_id,
                    book_id=book_id,
                    content=chunk_text.replace("\x00", ""),
                    page_number=page_number,
                    embedding=embedding,
                )
            )
        await self._session.flush()

    async def _generate_structure(
        self,
        book_id: UUID,
        book_title: str,
        total_pages: int,
        toc: list[list],
        page_samples: list[dict[str, int | str]],
    ) -> list[dict[str, object]]:
        """Try AI enrichment first, fall back to raw TOC if AI fails."""
        self._emit(book_id, "Analyzing structure with AI...")
        try:
            return await self._claude_service.generate_structure(
                book_title=book_title,
                total_pages=total_pages,
                base_toc=toc,
                page_samples=page_samples,
            )
        except Exception:
            logger.warning(
                "AI structure generation failed for book %s, falling back to raw TOC",
                book_id,
            )
            return self._toc_to_structure(toc, total_pages)

    @staticmethod
    def _toc_to_structure(
        toc: list[list], total_pages: int
    ) -> list[dict[str, object]]:
        """Convert PyMuPDF TOC to a hierarchical chapter structure.

        PyMuPDF TOC entries are [level, title, page] where level indicates nesting depth.
        Builds a tree by tracking a stack of parent nodes at each level.
        """
        if not toc:
            return [{"title": "Full Book", "start_page": 1, "end_page": total_pages, "children": []}]

        # First pass: build flat list with levels and compute end pages
        flat: list[dict[str, object]] = []
        for i, entry in enumerate(toc):
            level = int(entry[0]) if len(entry) > 0 else 1
            title = str(entry[1]).replace("\x00", "").strip() if len(entry) > 1 else f"Chapter {i + 1}"
            start_page = int(entry[2]) if len(entry) > 2 else 1
            # End page: next entry's start - 1, or total_pages for the last
            next_start = int(toc[i + 1][2]) - 1 if i + 1 < len(toc) and len(toc[i + 1]) > 2 else total_pages
            end_page = max(next_start, start_page)
            flat.append({
                "level": level,
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
                "children": [],
            })

        # Second pass: build tree using a stack
        root: list[dict[str, object]] = []
        stack: list[dict[str, object]] = []  # stack of (node, level) ancestors

        for item in flat:
            level = item.pop("level")
            # Pop stack until we find a parent at a lower level
            while stack and stack[-1][1] >= level:
                stack.pop()

            if stack:
                parent = stack[-1][0]
                parent["children"].append(item)  # type: ignore[union-attr]
            else:
                root.append(item)

            stack.append((item, level))

        # Fix end pages for parent nodes to span their children
        def _fix_end_pages(nodes: list[dict[str, object]]) -> None:
            for node in nodes:
                children = node.get("children", [])
                if children:
                    _fix_end_pages(children)  # type: ignore[arg-type]
                    node["end_page"] = max(
                        int(node["end_page"]),  # type: ignore[arg-type]
                        max(int(c["end_page"]) for c in children),  # type: ignore[index]
                    )

        _fix_end_pages(root)
        return root

    def _emit(self, book_id: UUID, step: str) -> None:
        if self._tracker:
            self._tracker.emit(book_id, step)

    def _emit_complete(self, book_id: UUID, step: str) -> None:
        if self._tracker:
            self._tracker.emit(book_id, step)
            self._tracker.complete(book_id)

    def _extract_metadata(self, book: Book, doc: fitz.Document) -> None:
        metadata = doc.metadata
        if metadata:
            if metadata.get("title"):
                book.title = metadata["title"].replace("\x00", "").strip()
            if metadata.get("author"):
                book.author = metadata["author"].replace("\x00", "").strip()
        book.page_count = len(doc)

    def _extract_page_samples(self, doc: fitz.Document) -> list[dict[str, int | str]]:
        page_samples: list[dict[str, int | str]] = []
        sample_count = min(len(doc), _MAX_SAMPLE_PAGES)
        for i in range(sample_count):
            page_text = doc[i].get_text()
            if page_text.strip():
                page_samples.append({"page": i + 1, "text": page_text[:_MAX_TEXT_PER_PAGE]})
        return page_samples

    async def _save_chapters(
        self,
        book_id: UUID,
        structure: list[dict[str, object]],
        parent_id: UUID | None = None,
        level: int = 0,
    ) -> None:
        for order, item in enumerate(structure):
            chapter = Chapter(
                book_id=book_id,
                parent_id=parent_id,
                title=str(item.get("title", "Untitled")).replace("\x00", "").strip(),
                level=level,
                order=order,
                start_page=int(item.get("start_page", 1)),
                end_page=int(item.get("end_page", 1)),
            )
            self._session.add(chapter)
            await self._session.flush()

            children = item.get("children")
            if children and isinstance(children, list):
                await self._save_chapters(book_id, children, parent_id=chapter.id, level=level + 1)

    async def _embed_chapters(
        self,
        book_id: UUID,
        file_path: str,
        strategy: ChunkingStrategy = ChunkingStrategy.HEADINGS,
    ) -> None:
        """Extract text from leaf chapters, chunk, and store embeddings in batches.

        Uses the TOC hierarchy as the primary chunking strategy:
        - Each leaf chapter becomes one or more chunks
        - Chapters under _MIN_CHUNK_SIZE are merged with the next sibling
        - Chapters over _MAX_CHUNK_SIZE are sub-split with overlap
        - Falls back to heading detection only if there's no TOC (single "Full Book" chapter)
        """
        result = await self._session.execute(
            select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.order)
        )
        chapters = list(result.scalars().all())

        parent_ids = {c.parent_id for c in chapters if c.parent_id}
        leaf_chapters = [c for c in chapters if c.id not in parent_ids]

        doc = fitz.open(file_path)

        # Phase 1: Extract text per leaf chapter, then chunk
        self._emit(book_id, "Chunking text...")
        chunk_records: list[tuple[str, UUID, int]] = []  # (text, chapter_id, page_number)
        all_texts: list[str] = []

        # If there's only one chapter (no real TOC), fall back to heading detection
        use_toc_chunking = len(leaf_chapters) > 1

        if use_toc_chunking:
            # TOC-based: each leaf chapter is a semantic unit
            pending_text = ""
            pending_chapter: Chapter | None = None

            for chapter in leaf_chapters:
                chapter_text = self._extract_chapter_text(doc, chapter)
                if not chapter_text.strip():
                    continue

                # Merge small chapters with pending buffer
                if pending_text and len(pending_text) < _MIN_CHUNK_SIZE:
                    pending_text += "\n" + chapter_text
                    # Keep the original pending_chapter for the chunk record
                else:
                    # Flush pending buffer
                    if pending_text:
                        self._add_chapter_chunks(
                            pending_text, pending_chapter, book_id,
                            all_texts, chunk_records,
                        )
                    pending_text = chapter_text
                    pending_chapter = chapter

            # Flush last pending
            if pending_text and pending_chapter:
                self._add_chapter_chunks(
                    pending_text, pending_chapter, book_id,
                    all_texts, chunk_records,
                )
        else:
            # No TOC — fall back to heading detection or fixed chunking
            for chapter in leaf_chapters:
                chunks = self._get_pdf_chunks(doc, chapter, strategy)
                if not chunks:
                    continue
                for chunk_text in chunks:
                    all_texts.append(chunk_text)
                    chunk_records.append((chunk_text, chapter.id, chapter.start_page))

        doc.close()

        if not all_texts:
            return

        # Phase 2: Encode all chunks in batches
        batch_size = 64
        all_embeddings: list[list[float]] = []
        total_chunks = len(all_texts)
        for i in range(0, total_chunks, batch_size):
            batch = all_texts[i : i + batch_size]
            self._emit(book_id, f"Encoding embeddings... ({min(i + batch_size, total_chunks)}/{total_chunks})")
            embeddings = await self._embedding_service.encode_async(batch)
            all_embeddings.extend(embeddings)

        # Phase 3: Insert all chunk embeddings
        self._emit(book_id, "Saving to database...")
        for (chunk_text, chapter_id, page_number), embedding in zip(chunk_records, all_embeddings):
            self._session.add(
                ChunkEmbedding(
                    chapter_id=chapter_id,
                    book_id=book_id,
                    content=chunk_text.replace("\x00", ""),
                    page_number=page_number,
                    embedding=embedding,
                )
            )

            await self._session.flush()

        doc.close()

    @staticmethod
    def _extract_chapter_text(doc: fitz.Document, chapter: Chapter) -> str:
        """Extract raw text from a chapter's page range."""
        parts = []
        for page_num in range(chapter.start_page - 1, min(chapter.end_page, len(doc))):
            parts.append(doc[page_num].get_text())
        return "\n".join(parts)

    @staticmethod
    def _add_chapter_chunks(
        text: str,
        chapter: Chapter,
        book_id: UUID,
        all_texts: list[str],
        chunk_records: list[tuple[str, UUID, int]],
    ) -> None:
        """Add chunks for a chapter's text, sub-splitting if too large."""
        text = text.strip()
        if not text:
            return
        if len(text) <= _MAX_CHUNK_SIZE:
            all_texts.append(text)
            chunk_records.append((text, chapter.id, chapter.start_page))
        else:
            sub_chunks = ProcessingService._chunk_text(text)
            for chunk in sub_chunks:
                all_texts.append(chunk)
                chunk_records.append((chunk, chapter.id, chapter.start_page))

    @staticmethod
    def _get_pdf_chunks(
        doc: fitz.Document,
        chapter: Chapter,
        strategy: ChunkingStrategy,
    ) -> list[str]:
        """Get chunks for a PDF chapter using the specified strategy."""
        if strategy == ChunkingStrategy.HEADINGS:
            chunks = ProcessingService._chunk_text_by_headings_pdf(
                doc, chapter.start_page, chapter.end_page
            )
            if chunks:
                return chunks
            # Fall through to fixed if headings produced nothing

        # Fixed-size chunking
        chapter_text = ""
        for page_num in range(chapter.start_page - 1, min(chapter.end_page, len(doc))):
            chapter_text += doc[page_num].get_text() + "\n"
        if not chapter_text.strip():
            return []
        return ProcessingService._chunk_text(chapter_text)

    @staticmethod
    def _chunk_text(
        text: str,
        chunk_size: int = _CHUNK_SIZE,
        overlap: int = _CHUNK_OVERLAP,
    ) -> list[str]:
        """Split text into fixed-size overlapping chunks (fallback)."""
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return [c for c in chunks if c.strip()]

    @staticmethod
    def _chunk_text_by_headings_pdf(doc: fitz.Document, start_page: int, end_page: int) -> list[str]:
        """Split PDF text into chunks based on font-size heading detection.

        Detects headings by finding text spans with font size significantly
        larger than the median body font size. Splits on those boundaries.
        Falls back to fixed-size chunking for sections that are too large.
        """
        # Collect all spans with font sizes across pages
        sections: list[dict[str, object]] = []
        current_section_lines: list[str] = []
        body_font_sizes: list[float] = []

        for page_num in range(start_page - 1, min(end_page, len(doc))):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            for block in blocks:
                if block.get("type") != 0:  # skip non-text blocks (images)
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        body_font_sizes.append(span["size"])

        if not body_font_sizes:
            return []

        # Determine median body font size
        sorted_sizes = sorted(body_font_sizes)
        median_size = sorted_sizes[len(sorted_sizes) // 2]
        heading_threshold = median_size * 1.15  # 15% larger = heading

        # Second pass: split on headings
        for page_num in range(start_page - 1, min(end_page, len(doc))):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    line_text = "".join(span["text"] for span in line.get("spans", []))
                    max_font_size = max((span["size"] for span in line.get("spans", [])), default=0)

                    is_heading = (
                        max_font_size >= heading_threshold
                        and len(line_text.strip()) < 200  # headings are short
                        and line_text.strip()
                    )

                    if is_heading and current_section_lines:
                        # Save previous section, start new one
                        sections.append({"text": "\n".join(current_section_lines)})
                        current_section_lines = [line_text]
                    else:
                        current_section_lines.append(line_text)

        # Don't forget the last section
        if current_section_lines:
            sections.append({"text": "\n".join(current_section_lines)})

        # Build chunks: use sections directly, sub-split if too large
        raw_chunks: list[str] = []
        for section in sections:
            text = str(section["text"]).strip()
            if not text:
                continue
            if len(text) <= _MAX_CHUNK_SIZE:
                raw_chunks.append(text)
            else:
                sub_chunks = ProcessingService._chunk_text(text)
                raw_chunks.extend(sub_chunks)

        # Merge small chunks with the next one to avoid tiny fragments
        chunks: list[str] = []
        for chunk in raw_chunks:
            if chunks and len(chunks[-1]) < _MIN_CHUNK_SIZE:
                chunks[-1] = chunks[-1] + "\n" + chunk
            else:
                chunks.append(chunk)

        return chunks

    @staticmethod
    def _chunk_epub_html_by_headings(html_content: str) -> list[str]:
        """Split EPUB HTML content into chunks based on h2/h3 headings.

        Falls back to fixed-size chunking for sections that are too large.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        heading_tags = {"h1", "h2", "h3"}

        sections: list[str] = []
        current_parts: list[str] = []

        for element in soup.descendants:
            if element.name in heading_tags:
                # Save accumulated text as a section
                section_text = " ".join(current_parts).strip()
                if section_text:
                    sections.append(section_text)
                current_parts = [element.get_text(strip=True)]
            elif element.string and element.string.strip():
                # Only collect leaf text nodes
                if not any(child.name for child in getattr(element, "children", [])):
                    current_parts.append(element.string.strip())

        # Last section
        section_text = " ".join(current_parts).strip()
        if section_text:
            sections.append(section_text)

        # Build chunks: use sections directly, sub-split if too large
        chunks: list[str] = []
        for text in sections:
            if not text:
                continue
            if len(text) <= _MAX_CHUNK_SIZE:
                chunks.append(text)
            else:
                sub_chunks = ProcessingService._chunk_text(text)
                chunks.extend(sub_chunks)

        return chunks
