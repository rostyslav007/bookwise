<!--
This document describes HOW to build the feature at an architectural level.
-->

# Technical Specification: EPUB Support

- **Functional Specification:** `context/spec/006-epub-support/functional-spec.md`
- **Status:** Completed
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

EPUB support touches four layers:

1. **Data model:** Add a `format` field to the `Book` model to distinguish PDF from EPUB.
2. **Backend processing:** Create an `EpubParserService` (using `ebooklib`) that extracts metadata, TOC, and chapter text from EPUBs — plugging into the existing `ProcessingService` pipeline.
3. **Backend serving:** Add an endpoint to serve raw EPUB files (like the existing PDF endpoint).
4. **Frontend viewer:** Add an `EpubViewerPage` using `epub.js` for native EPUB rendering with chapter navigation. The book detail page and MCP results route to the correct viewer based on format.

The existing chunking, embedding, search, and MCP layers require no changes — they work on text regardless of source format.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Data Model: Add `format` to Book

**File:** `backend/app/models/book.py`

Add an enum and field:
```python
class BookFormat(str, enum.Enum):
    PDF = "pdf"
    EPUB = "epub"
```

Add column: `format: Mapped[str] = mapped_column(String, nullable=False, default=BookFormat.PDF.value)`

**Migration:** Add `format` column to `books` table with default `"pdf"` (so existing books are unaffected).

**File:** `backend/app/schemas/book.py`

Add `format: str` to `BookResponse`.

### 2.2. Upload: Accept EPUB

**File:** `backend/app/services/book_service.py`

Update `upload_and_create`:
- Accept `application/pdf` and `application/epub+zip` MIME types
- Determine format from MIME type
- Save with correct extension (`.pdf` or `.epub`)
- Store format in the book record

### 2.3. EPUB Parser Service

**New dependency:** `ebooklib>=0.18,<1.0`

**File:** `backend/app/services/epub_parser_service.py`

```python
class EpubParserService:
    def extract_metadata(self, file_path: str) -> dict[str, str | None]:
        """Extract title, author from EPUB metadata."""

    def extract_toc(self, file_path: str) -> list[list]:
        """Extract TOC in same format as PyMuPDF: [[level, title, page/order], ...]"""

    def extract_chapter_text(self, file_path: str, chapter_href: str) -> str:
        """Extract text content from a specific EPUB chapter by its href."""

    def extract_all_text(self, file_path: str) -> list[dict[str, str]]:
        """Extract all chapter texts for indexing. Returns [{title, text, order}, ...]"""
```

EPUB chapters are identified by href (not page numbers). The `Chapter` model's `start_page`/`end_page` can store chapter order index for EPUBs (since EPUBs don't have fixed pages).

### 2.4. Processing Pipeline: Format Routing

**File:** `backend/app/services/processing_service.py`

Update `process_book` to branch on format:
- **PDF:** Existing PyMuPDF flow (unchanged)
- **EPUB:** Use `EpubParserService` for metadata, TOC, and text extraction. Then feed into the same chunking + embedding pipeline.

The key difference: EPUB text is extracted per-chapter (via `ebooklib` spine/items), not per-page. Chunking and embedding work the same way on the extracted text.

### 2.5. EPUB File Serving

**File:** `backend/app/routers/books.py`

Update the existing `/api/v1/books/{book_id}/pdf` endpoint or add a generic `/api/v1/books/{book_id}/file` endpoint that serves the raw file with the correct MIME type based on format.

### 2.6. Frontend: EPUB Viewer Page

**New dependency:** `epub.js` (`npm install epubjs`)

**File:** `frontend/src/pages/EpubViewerPage.tsx`

- Route: `/books/:bookId/epub`
- Uses `epub.js` to render the EPUB file fetched from `/api/v1/books/{bookId}/file`
- Chapter navigation sidebar (from EPUB TOC)
- Font size / theme controls
- Opens at a specific chapter via URL parameter `?chapter=href`
- "Back to book" link

### 2.7. Frontend: Format-Aware Routing

**Files:** `BookDetailPage.tsx`, `ChapterItem.tsx`, `SearchPage.tsx`

- "View PDF" button becomes "View Book" — routes to `/books/{id}/view` for PDFs or `/books/{id}/epub` for EPUBs based on `book.format`
- Search result `viewer_url` routes to the correct viewer
- Chapter click navigates to the correct viewer

### 2.8. MCP: Format-Aware viewer_url

**File:** `backend/app/services/search_service.py`

Update `viewer_url` construction: use `/books/{id}/epub?chapter=...` for EPUB books instead of `/books/{id}/view?page=N`.

### 2.9. MCP: get_chapter_content for EPUB

**File:** `backend/app/mcp_server.py`

Update `get_chapter_content`: for EPUB books, use `EpubParserService.extract_chapter_text()` instead of PyMuPDF page extraction.

---

## 3. Impact and Risk Analysis

- **System Dependencies:** Adds `ebooklib` (Python) and `epubjs` (JS). No database schema changes beyond one new column.
- **Potential Risks:**
  - **EPUB chapter identification:** EPUBs use href-based chapter references, not page numbers. The `Chapter` model's `start_page`/`end_page` fields will store order indices for EPUBs. This is a semantic mismatch but avoids a schema change.
  - **epub.js bundle size:** ~500KB. Mitigated by lazy-loading the viewer page.
  - **Malformed EPUBs:** Some EPUBs have non-standard structure. `ebooklib` handles most cases but edge cases exist.

---

## 4. Testing Strategy

- **Backend:** Test EPUB upload, metadata extraction, chapter text extraction, and chunking with a sample EPUB file.
- **Frontend:** Test EpubViewerPage renders and navigates chapters.
- **E2E:** Upload an EPUB, verify processing, search, and viewer.
