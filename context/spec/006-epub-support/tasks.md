# Tasks: EPUB Support

---

## Slice 1: EPUB Upload + Processing

_Goal: User can upload an EPUB file. The system extracts metadata, chapters, and indexes content for search. Book shows as "ready"._

- [x] **Slice 1: EPUB upload and processing**
  - [x] Add `BookFormat` enum and `format` column to `Book` model. Create Alembic migration (default `"pdf"` for existing books). Add `format` to `BookResponse` schema. **[Agent: general-purpose]**
  - [x] Update `BookService.upload_and_create` to accept `application/epub+zip` alongside PDF. Save with correct extension, store format. Update frontend upload zone to accept `.epub` files. **[Agent: general-purpose]**
  - [x] Add `ebooklib` to requirements. Create `EpubParserService` with methods: `extract_metadata`, `extract_toc`, `extract_chapter_texts`. **[Agent: general-purpose]**
  - [x] Update `ProcessingService.process_book` to branch on format: use `EpubParserService` for EPUB books (metadata, TOC, text extraction), then feed into existing chunking + embedding pipeline. **[Agent: general-purpose]**
  - [x] **Verify:** Upload an EPUB file. Verify status transitions to "ready", chapters are extracted, and search returns results from the EPUB book. **[Agent: general-purpose]**

---

## Slice 2: EPUB Viewer + Format-Aware Routing

_Goal: EPUB books open in a dedicated epub.js reader. PDF and EPUB books route to the correct viewer throughout the UI._

- [x] **Slice 2: EPUB viewer and routing**
  - [x] Add generic `GET /api/v1/books/{book_id}/file` endpoint that serves the raw file (PDF or EPUB) with correct MIME type. **[Agent: general-purpose]**
  - [x] Install `epubjs`. Create `EpubViewerPage` at `/books/:bookId/epub` with epub.js renderer, chapter navigation, font size controls, and `?chapter=href` URL param support. Add lazy-loaded route to `App.tsx`. **[Agent: general-purpose]**
  - [x] Update `BookDetailPage` to show "View EPUB" or "View PDF" based on format. Update `ChapterItem` click and `SearchPage` result links to route to the correct viewer. **[Agent: general-purpose]**
  - [x] Update `search_service.py` to build `viewer_url` based on book format (EPUB → `/epub?chapter=...`, PDF → `/view?page=...`). Update `mcp_server.py` `get_chapter_content` to use `EpubParserService` for EPUB books. **[Agent: general-purpose]**
  - [x] **Verify:** Upload an EPUB, navigate to book detail, click "View EPUB", verify reader renders with chapter navigation. Verify search results link to EPUB viewer. Verify PDF books still route to PDF viewer. **[Agent: general-purpose]**

---

## Slice 3: Tests

_Goal: Test coverage for EPUB upload, processing, and serving._

- [x] **Slice 3: Tests**
  - [x] Add backend tests: EPUB upload accepted, EPUB metadata extraction, EPUB chapter text extraction, EPUB file serving with correct MIME type. **[Agent: general-purpose]**
  - [x] **Verify:** Run `pytest`. All tests pass. **[Agent: general-purpose]**
