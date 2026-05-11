# Functional Specification: Search & Reading UI

- **Roadmap Item:** Search & Reading UI — Concept search from the browser, chapter browsing, integrated PDF viewer
- **Status:** Completed
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

The MCP server allows Claude to search books during coding sessions, but sometimes the user wants to search their book library directly — without going through Claude. A dedicated search page in the Web UI lets the user type a concept, see results across all books, and jump directly to the relevant page in the PDF viewer with highlighting.

The chapter browser and integrated PDF viewer are already implemented. This spec focuses on the missing piece: a Web UI concept search.

**Success looks like:** The user opens the search page, types "dependency injection", and sees a ranked list of results showing which books and chapters discuss it — with direct links to view the relevant PDF pages.

---

## 2. Functional Requirements (The "What")

### 2.1. Concept Search Page

- **As a** user, **I want to** search across all my books by concept, pattern, or topic from the browser, **so that** I can find relevant content without asking Claude.
  - **Acceptance Criteria:**
    - [x] A dedicated search page is accessible from the navigation (e.g., a "Search" link in the sidebar or header).
    - [x] The search page has a prominent search input where the user types a concept or topic.
    - [x] After submitting a search, results are displayed as a list ranked by relevance.
    - [x] Each result shows: book title, author, chapter title, page number, and a text snippet of the matching content.
    - [x] Each result has a "View in PDF" link that opens the PDF viewer at the correct page with the snippet text highlighted.
    - [x] If no results are found, a message says "No matches found in your library."

### 2.2. Already Implemented (No New Work)

The following requirements from the roadmap are already implemented:

- **Chapter Browser:** `BookDetailPage` shows a hierarchical chapter tree with edit/view actions. Clicking a chapter opens the PDF viewer at the chapter's start page.
- **Integrated PDF Viewer:** `PdfViewerPage` renders PDFs with page navigation, zoom, and text highlighting via URL parameters.

---

## 3. Scope and Boundaries

### In-Scope

- Dedicated search page at `/search` with semantic search across all books.
- Search results with book/chapter metadata and text snippets.
- Direct links from results to the PDF viewer with highlighting.
- Navigation link to the search page.

### Out-of-Scope

- Search filters (by group, by book) — nice to have but not v1.
- Search history or saved searches.
- Full-text search (keyword matching) — we use semantic vector search only.
