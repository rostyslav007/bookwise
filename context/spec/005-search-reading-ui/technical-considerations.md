<!--
This document describes HOW to build the feature at an architectural level.
-->

# Technical Specification: Search & Reading UI

- **Functional Specification:** `context/spec/005-search-reading-ui/functional-spec.md`
- **Status:** Completed
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

The semantic search logic already exists in `SearchService` (used by the MCP server). This feature adds:

1. **Backend:** A REST endpoint `GET /api/v1/search?q=...` that uses `SearchService` to perform vector search and returns results.
2. **Frontend:** A `/search` page with a search input, results list, and links to the PDF viewer.

No new services, models, or database changes needed.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Backend: Search REST Endpoint

**File:** `backend/app/routers/search.py`

New router with one endpoint:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/search?q={query}` | Semantic search across all books. Returns `SearchResult` (same schema as MCP). |

The endpoint:
- Takes `q: str` query parameter
- Creates `EmbeddingService` (lazy singleton) and `SearchService` with a database session
- Calls `service.search(query)`
- Returns the `SearchResult` response (list of `SearchHit` with `viewer_url`)

Register in `main.py`.

### 2.2. Frontend: Search Page

**File:** `frontend/src/pages/SearchPage.tsx`

- Route: `/search`
- A prominent search input with a search button/icon
- On submit, fetches `GET /api/v1/search/?q={encoded_query}` via TanStack Query
- Displays results as a card list, each showing: book title, author, chapter title, page number, snippet preview
- Each result has a "View in PDF" button/link using `viewer_url` from the response
- Empty state: "No matches found in your library."
- Loading state while search is in progress

**File:** `frontend/src/api/search.ts`

TanStack Query hook:
- `useSearch(query: string)` — enabled only when query is non-empty, fetches from `/api/v1/search/?q={query}`

### 2.3. Navigation

**File:** `frontend/src/App.tsx`

Add route: `/search` → `SearchPage`

Add a "Search" link to the navigation. Options:
- Add a search icon/link to the `GroupSidebar` header (above groups list)
- Or add a top-level nav bar

Simplest: add a "Search" button at the top of the sidebar, above the groups heading.

---

## 3. Impact and Risk Analysis

- **System Dependencies:** Reuses `SearchService` and `EmbeddingService` from the MCP server feature. No new dependencies.
- **Potential Risks:**
  - **Embedding model loading time:** First search may take a few seconds while the model loads. Mitigation: show loading state. Model is cached after first load.
  - **No books indexed:** If no books have been uploaded/processed, search returns empty. The UI should show a helpful message.

---

## 4. Testing Strategy

- **Backend:** Test the search REST endpoint returns correct response format. Test with no query param returns 422.
- **E2E:** Navigate to search page, type a query, verify results display (or empty state if no indexed books).
