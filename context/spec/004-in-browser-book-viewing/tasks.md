# Tasks: In-Browser Book Viewing

---

## Slice 1: PDF Serving + Basic Viewer

_Goal: User can open a PDF in the Web UI from the book detail page. The viewer shows pages with zoom/scroll and navigates to a specific page via URL parameter._

- [x] **Slice 1: PDF serving and basic viewer**
  - [x] Add `GET /api/v1/books/{book_id}/pdf` endpoint to backend that streams the PDF file via `FileResponse`. Returns 404 if book not found. **[Agent: general-purpose]**
  - [x] Install `@react-pdf-viewer/core`, `@react-pdf-viewer/default-layout`, `@react-pdf-viewer/page-navigation`, `pdfjs-dist` in frontend. Create `PdfViewerPage` at route `/books/:bookId/view` that loads PDF from `/api/v1/books/{bookId}/pdf`, renders the viewer with default layout (toolbar, zoom, scroll), and jumps to `?page=N` on load. Add route to `App.tsx`. **[Agent: general-purpose]**
  - [x] Add "View PDF" button to `BookDetailPage`. Add click-to-view on chapter items in `ChapterList` that navigates to `/books/{id}/view?page={start_page}`. **[Agent: general-purpose]**
  - [x] **Verify:** Navigate to a book detail page, click "View PDF", verify the PDF loads in the viewer with zoom/scroll. Navigate with `?page=5`, verify it opens at page 5. Click a chapter, verify it opens the viewer at the chapter's start page. **[Agent: general-purpose]**

---

## Slice 2: Text Highlighting + MCP URL

_Goal: The viewer highlights text snippets passed via URL. MCP search results include a clickable viewer URL._

- [x] **Slice 2: Highlighting and MCP integration**
  - [x] Install `@react-pdf-viewer/search` in frontend. Update `PdfViewerPage` to read `?highlight=text` query param and use `searchPlugin({ keyword: [highlightText] })` to auto-highlight matching text on the target page. **[Agent: general-purpose]**
  - [x] Add `frontend_url` to `backend/app/config.py` (default: `http://localhost:3000`). Update `SearchHit` in `search_service.py` to include `viewer_url` field. Build URL from book_id, page_number, and snippet (URL-encoded). **[Agent: general-purpose]**
  - [x] **Verify:** Open viewer with `?page=5&highlight=some+text`, verify text is highlighted and scrolled into view. Verify MCP `search_books` results include `viewer_url` field with correct format. **[Agent: general-purpose]**

---

## Slice 3: Tests

_Goal: Test coverage for PDF serving endpoint and viewer._

- [x] **Slice 3: Tests**
  - [x] Add backend test for `GET /api/v1/books/{id}/pdf`: verify returns PDF content-type and file content. Add test for 404 on nonexistent book. **[Agent: general-purpose]**
  - [x] **Verify:** Run `pytest` and `npm test`. All tests pass. **[Agent: general-purpose]**
