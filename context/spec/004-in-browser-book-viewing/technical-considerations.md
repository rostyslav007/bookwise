<!--
This document describes HOW to build the feature at an architectural level.
-->

# Technical Specification: In-Browser Book Viewing

- **Functional Specification:** `context/spec/004-in-browser-book-viewing/functional-spec.md`
- **Status:** Completed
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

This feature adds three things:

1. **Backend:** A PDF serving endpoint (`GET /api/v1/books/{id}/pdf`) that streams the raw PDF file.
2. **Frontend:** A PDF viewer page using `@react-pdf-viewer/react-pdf-viewer` with page navigation and text highlighting plugins. Route: `/books/{id}/view?page=N&highlight=text`.
3. **MCP:** Update `search_books` results to include a `viewer_url` field pointing to the Web UI viewer with page + highlight parameters.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Backend: PDF Serving Endpoint

**File:** `backend/app/routers/books.py`

Add endpoint:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/books/{book_id}/pdf` | Stream the raw PDF file with `Content-Type: application/pdf` |

Use FastAPI's `FileResponse` to serve the PDF from disk. Returns 404 if book not found.

### 2.2. Frontend: PDF Viewer Page

**New dependencies:**
```bash
npm install @react-pdf-viewer/core @react-pdf-viewer/default-layout @react-pdf-viewer/search @react-pdf-viewer/page-navigation pdfjs-dist
```

**New route:** `/books/:bookId/view` → `PdfViewerPage`

**File:** `frontend/src/pages/PdfViewerPage.tsx`

- Reads URL params: `bookId` from path, `page` and `highlight` from query string
- Fetches PDF from `/api/v1/books/{bookId}/pdf`
- Renders `<Viewer>` with:
  - `defaultLayoutPlugin` for toolbar (zoom, scroll, page navigation)
  - `searchPlugin` initialized with `keyword: [highlight]` when highlight param is present
  - `pageNavigationPlugin` to jump to the specified page on load
- Includes a "Back to book detail" link

**Key integration points:**
- `jumpToPage(pageNumber - 1)` on viewer load (pages are 0-indexed)
- `searchPlugin({ keyword: [highlightText] })` auto-highlights on load
- PDF URL: `/api/v1/books/${bookId}/pdf` (proxied through Nginx)

### 2.3. Frontend: "View PDF" Button on BookDetailPage

**File:** `frontend/src/pages/BookDetailPage.tsx`

Add a "View PDF" button that navigates to `/books/${bookId}/view`. When clicking a chapter in the chapter list, navigate to `/books/${bookId}/view?page=${chapter.start_page}`.

### 2.4. Frontend: Route Registration

**File:** `frontend/src/App.tsx`

Add route: `/books/:bookId/view` → `PdfViewerPage`

### 2.5. MCP: Add viewer_url to Search Results

**File:** `backend/app/services/search_service.py`

Update `SearchHit` to include a `viewer_url` field:
```python
class SearchHit(BaseModel):
    ...existing fields...
    viewer_url: str  # e.g., "http://localhost:3000/books/{book_id}/view?page=5&highlight=Observer+pattern"
```

Build the URL in the `search()` method using the book_id, page_number, and snippet text (URL-encoded). The base URL can be a config value (default: `http://localhost:3000`).

**File:** `backend/app/config.py`

Add: `frontend_url: str = "http://localhost:3000"`

---

## 3. Impact and Risk Analysis

- **System Dependencies:** Adds `@react-pdf-viewer` to frontend (pdf.js-based). The backend endpoint is a simple file serve.
- **Potential Risks & Mitigations:**
  - **Large PDF files:** Streaming via `FileResponse` handles this efficiently without loading the entire file into memory.
  - **pdf.js bundle size:** The pdfjs-dist library is ~1.5MB. Mitigation: lazy-load the viewer page (React.lazy + Suspense) so it doesn't affect the main bundle.
  - **Highlight accuracy:** Text highlighting depends on exact text match in the rendered PDF. If the snippet from the embedding chunk doesn't exactly match the PDF renderer's text, highlighting may miss. Mitigation: use a short, distinctive portion of the snippet for highlighting.

---

## 4. Testing Strategy

- **Backend:** Test the PDF serving endpoint returns correct content-type and file content.
- **Frontend:** Component test that PdfViewerPage renders with the viewer. E2E test that navigates to a viewer URL and verifies the PDF loads.
