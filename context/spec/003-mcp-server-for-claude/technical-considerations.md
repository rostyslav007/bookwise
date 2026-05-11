<!--
This document describes HOW to build the feature at an architectural level.
-->

# Technical Specification: MCP Server for Claude

- **Functional Specification:** `context/spec/003-mcp-server-for-claude/functional-spec.md`
- **Status:** Completed
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

Create a standalone Python MCP server using the `mcp` Python SDK's `FastMCP` class. The server:

- Runs via **stdio transport** — Claude Code launches it as a subprocess
- Connects directly to the existing PostgreSQL database (same connection string as the backend)
- Uses the existing `EmbeddingService` (sentence-transformers) to encode search queries into vectors
- Queries `chunk_embeddings` via pgvector's cosine similarity for semantic search
- Reads PDF page text via PyMuPDF for chapter content retrieval

The MCP server is a **separate entry point** from the FastAPI backend — it shares the same models/config but runs independently.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Project Structure

```
backend/
  app/
    mcp_server.py          # MCP server entry point with FastMCP tools
    services/
      search_service.py    # Semantic search logic (pgvector queries)
    ... (existing files)
```

The MCP server reuses existing modules: `app.config`, `app.database`, `app.models.*`, `app.services.embedding_service`.

### 2.2. Dependencies

Add to `backend/requirements.txt`:
- `mcp[cli]>=1.12,<2.0` — MCP Python SDK with CLI support

### 2.3. MCP Server Entry Point

**File: `backend/app/mcp_server.py`**

Uses `FastMCP` with two tool definitions:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="BooksNavigationMCP",
    instructions="Search the user's personal technical book library. "
                 "Use search_books to find concepts, patterns, and topics. "
                 "Results come from the user's own book collection."
)

@mcp.tool()
async def search_books(query: str) -> SearchResult:
    """Search the user's book library by concept or topic.
    Returns up to 5 results with book title, chapter, page, and text snippet.
    Use this to find where concepts are discussed in the user's technical books."""
    ...

@mcp.tool()
async def get_chapter_content(chapter_id: str) -> ChapterContent:
    """Retrieve the full text content of a specific chapter or section.
    Use a chapter_id from search_books results to get detailed content."""
    ...
```

Run with: `mcp.run(transport="stdio")`

### 2.4. Search Service

**File: `backend/app/services/search_service.py`**

New service that performs semantic vector search:

| Method | Description |
|---|---|
| `search(query: str, limit: int = 5) -> list[SearchHit]` | Encode query with EmbeddingService, query pgvector for nearest neighbors, join with chapters and books tables to get metadata |

The SQL query uses pgvector's cosine distance operator:

```sql
SELECT ce.content, ce.page_number, ce.chapter_id,
       c.title AS chapter_title, c.start_page, c.end_page,
       b.title AS book_title, b.author
FROM chunk_embeddings ce
JOIN chapters c ON ce.chapter_id = c.id
JOIN books b ON ce.book_id = b.id
ORDER BY ce.embedding <=> :query_embedding
LIMIT :limit
```

### 2.5. Tool Response Schemas

**search_books response:**
```python
class SearchHit(BaseModel):
    book_title: str
    author: str | None
    chapter_title: str
    chapter_id: str
    page_number: int
    snippet: str          # text chunk content (truncated to ~500 chars)
    relevance_score: float
    source: str           # always "library"

class SearchResult(BaseModel):
    results: list[SearchHit]
    source: str           # "library" if results found, "not_found" if empty
    message: str          # e.g., "Found 3 results" or "No matches found in your book library"
```

**get_chapter_content response:**
```python
class ChapterContent(BaseModel):
    chapter_title: str
    book_title: str
    author: str | None
    start_page: int
    end_page: int
    content: str          # full text extracted from PDF pages
    source: str           # "library"
```

### 2.6. Database Connection

The MCP server needs a synchronous or async SQLAlchemy connection. Since `FastMCP` tools can be `async`, use the existing async engine pattern from `app.database`. However, the MCP server runs as a standalone process (not inside the FastAPI app), so it needs to create its own engine instance at startup.

The database URL should point to `localhost:5432` (not `db:5432`) since the MCP server runs on the host, not inside Docker. Use an environment variable or the existing `.env` file with an override.

### 2.7. Claude Code Configuration

**File: `.mcp.json`** (project-level MCP config)

Add the BooksNavigationMCP server entry:
```json
{
  "mcpServers": {
    "books-navigation": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "backend", "python", "-m", "app.mcp_server"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/books"
      }
    }
  }
}
```

---

## 3. Impact and Risk Analysis

- **System Dependencies:** Reuses existing models, config, and EmbeddingService. Requires PostgreSQL to be running (via Docker Compose).
- **Potential Risks & Mitigations:**
  - **Model loading time:** sentence-transformers takes a few seconds to load on first search. Mitigation: lazy loading (already implemented in EmbeddingService).
  - **Database URL mismatch:** MCP server runs on host (localhost) but backend runs in Docker (db). Mitigation: pass `DATABASE_URL` override via `.mcp.json` env.
  - **Large chapter content:** Some chapters span many pages. Mitigation: truncate content to a reasonable limit (e.g., 10,000 chars) in get_chapter_content.

---

## 4. Testing Strategy

- **Unit tests:** Test `SearchService.search()` against a real PostgreSQL with sample embeddings. Test tool response schemas.
- **Integration test:** Run the MCP server, connect a test client via stdio, call both tools, verify responses.
- **Manual test:** Configure in Claude Code, ask about a concept, verify search results appear.
