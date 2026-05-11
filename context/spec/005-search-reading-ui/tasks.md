# Tasks: Search & Reading UI

---

## Slice 1: Search Endpoint + Search Page

_Goal: User can navigate to a search page, type a concept, and see ranked results with links to the PDF viewer._

- [x] **Slice 1: Concept search end-to-end**
  - [x] Create `backend/app/routers/search.py` with `GET /api/v1/search?q={query}` endpoint using `SearchService` and lazy `EmbeddingService`. Register in `main.py`. **[Agent: general-purpose]**
  - [x] Create `frontend/src/api/search.ts` with `useSearch(query)` TanStack Query hook. Create `frontend/src/pages/SearchPage.tsx` with search input, results list (book title, author, chapter, page, snippet), "View in PDF" links using `viewer_url`. Add route `/search` to `App.tsx`. Add "Search" link to `GroupSidebar`. **[Agent: general-purpose]**
  - [x] **Verify:** Navigate to `/search`, type a query, verify results display (or empty state). Click "View in PDF", verify PDF viewer opens at correct page with highlighting. Verify "Search" link is visible in sidebar. **[Agent: general-purpose]**

---

## Slice 2: Tests

_Goal: Test coverage for search endpoint._

- [x] **Slice 2: Tests**
  - [x] Add backend test for `GET /api/v1/search?q=...`: verify returns results with correct schema. Test empty query returns 422. **[Agent: general-purpose]**
  - [x] **Verify:** Run `pytest`. All tests pass. **[Agent: general-purpose]**
