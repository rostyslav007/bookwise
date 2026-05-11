# Tasks: MCP Server for Claude

---

## Slice 1: Search Service + MCP Server with search_books tool

_Goal: A working MCP server with stdio transport that Claude Code can connect to. The `search_books` tool performs semantic search over book embeddings and returns results with book/chapter/page references._

- [x] **Slice 1: search_books tool via MCP**
  - [x] Add `mcp[cli]` to `backend/requirements.txt`. Create `backend/app/services/search_service.py` with `SearchService` class: accepts `AsyncSession` and `EmbeddingService`, has `search(query, limit=5)` method that encodes query to vector, queries pgvector with cosine distance joining chunks/chapters/books, returns results. **[Agent: general-purpose]**
  - [x] Create `backend/app/mcp_server.py` with `FastMCP` server. Define `search_books` tool that creates a database session, instantiates `SearchService` + `EmbeddingService`, calls `search()`, returns `SearchResult` with source metadata (`"library"` or `"not_found"`). Run with `mcp.run(transport="stdio")`. **[Agent: general-purpose]**
  - [x] Update `.mcp.json` to add the `books-navigation` MCP server entry with stdio transport pointing to `uv run --directory backend python -m app.mcp_server`. **[Agent: general-purpose]**
  - [x] **Verify:** Run the MCP server manually, connect a test client or use `mcp dev`, call `search_books` with a query, verify results are returned (or empty set if no books indexed). **[Agent: general-purpose]**

---

## Slice 2: get_chapter_content tool

_Goal: Claude can retrieve the full text of a specific chapter by ID, extracted from the PDF._

- [x] **Slice 2: get_chapter_content tool**
  - [x] Add `get_chapter_content` tool to `backend/app/mcp_server.py`: accepts `chapter_id`, looks up the chapter and its book, extracts text from the PDF page range using PyMuPDF, returns `ChapterContent` with metadata and source. Truncate to 10,000 chars if needed. **[Agent: general-purpose]**
  - [x] **Verify:** Call `get_chapter_content` with a valid chapter ID, verify full text and metadata are returned. Call with invalid ID, verify appropriate error. **[Agent: general-purpose]**

---

## Slice 3: Tests

_Goal: Test coverage for the search service and MCP tools._

- [x] **Slice 3: Backend tests for MCP**
  - [x] Add tests for `SearchService`: test search with sample embeddings returns ranked results, test search with no matches returns empty. Test response schemas. **[Agent: general-purpose]**
  - [x] **Verify:** Run `pytest`. All tests pass. **[Agent: general-purpose]**
