# Functional Specification: In-Browser Book Viewing

- **Roadmap Item:** In-Browser Book Viewing — Open PDFs at exact page, highlight relevant text
- **Status:** Completed
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

When Claude finds a concept in the user's book library, the user currently gets a text reference (book title, chapter, page number). But to actually re-read the source material, the user needs to manually find and open the PDF. This feature bridges that gap by embedding a PDF viewer in the Web UI that opens at the exact page with relevant text highlighted — and making it accessible from Claude via a shareable URL.

**Success looks like:** Claude says "The Observer pattern is in Design Patterns, Chapter 5, page 293" and provides a link. The user clicks it, and the Web UI opens with the PDF at page 293, with the relevant passage highlighted.

---

## 2. Functional Requirements (The "What")

### 2.1. Integrated PDF Viewer

- **As a** user, **I want to** view my uploaded PDFs directly in the Web UI, **so that** I can read book content without switching to a separate PDF reader.
  - **Acceptance Criteria:**
    - [x] The book detail page has a "View PDF" button that opens the PDF viewer.
    - [x] The PDF viewer displays the book's pages with readable text, scrolling, and zoom controls.
    - [x] The viewer opens at a specific page when a page number is provided (e.g., via URL parameter).

### 2.2. Text Highlighting

- **As a** user, **I want to** see relevant text passages highlighted in the PDF viewer, **so that** I can immediately find the content Claude referenced.
  - **Acceptance Criteria:**
    - [x] When the viewer is opened with a highlight parameter (a text snippet), the matching text on the page is visually highlighted.
    - [x] The highlight scrolls into view automatically so the user doesn't need to search for it.

### 2.3. MCP URL Integration

- **As a** user, **I want** Claude to share a clickable link that opens the PDF at the right page with highlights, **so that** I can jump from a Claude conversation directly into the book.
  - **Acceptance Criteria:**
    - [x] The MCP server has a tool or returns a URL in search results pointing to the Web UI PDF viewer with the correct page and highlight parameters.
    - [x] The URL format is something like: `http://localhost:3000/books/{id}/view?page=N&highlight=text`
    - [x] Clicking the URL in the terminal or browser opens the viewer at the right page with the text highlighted.

### 2.4. PDF Serving

- **As a** user, **I want** the Web UI to load the PDF file from the backend, **so that** the viewer can display it.
  - **Acceptance Criteria:**
    - [x] The backend serves the raw PDF file via an endpoint (e.g., `GET /api/v1/books/{id}/pdf`).
    - [x] The frontend PDF viewer fetches and renders the PDF from this endpoint.

---

## 3. Scope and Boundaries

### In-Scope

- Embedded PDF viewer in the Web UI using pdf.js (or similar library).
- Open at specific page via URL parameter.
- Text highlighting of matched snippets.
- Backend endpoint to serve raw PDF files.
- MCP search results include a viewer URL with page + highlight parameters.

### Out-of-Scope

- **Web UI concept search** — Phase 3 roadmap item.
- **Chapter browser in Web UI** — Phase 3 roadmap item.
- PDF annotation or editing.
- Bookmarks or reading position tracking.
- Mobile-optimized PDF viewing.
