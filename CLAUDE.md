# Bookwise (BooksNavigationMCP)

Personal technical book RAG system — upload PDF/EPUB books, index with vector embeddings, search via semantic similarity, chat with Claude about your library.

## Stack

- **Backend:** Python 3.12 FastAPI + PostgreSQL/pgvector + PyMuPDF + ebooklib
- **Frontend:** React 19 + TypeScript + Vite + Tailwind/shadcn + react-pdf + epubjs
- **MCP Server:** Python MCP SDK (stdio) — `search_books` + `get_chapter_content` + `explain_from_book`
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384-dim, local)
- **Chat:** Claude Sonnet via AWS Bedrock (configurable, falls back to direct Anthropic API)
- **Deployment:** Docker Compose (backend:8000, frontend:3000, postgres:5432)

## Architecture

```
Upload PDF/EPUB → Extract metadata + TOC → AI structure enrichment (optional)
→ Save chapters (hierarchical) → Chunk text (TOC-based, heading-based, or fixed)
→ Embed with sentence-transformers (encode_async, thread pool) → Store in pgvector

Search query → Embed → Cosine similarity → Ranked results with viewer_url
Chat → Claude tool_use API (search_books + explain_from_book) → streaming response with book citations
```

## Key Patterns

- **Lazy singleton** for EmbeddingService — loaded once, reused globally
- **SSE streaming** for processing progress + chat responses
- **Chunking strategies:** TOC-based (primary for PDF with real TOC — leaf chapters as semantic units, sub-split >4000, merge <200), heading detection (fallback for no TOC — font-size heuristic), EPUB h1/h2/h3 splitting, fixed (2000 chars / 400 overlap)
- **AI fallback:** Claude structure generation fails → raw PyMuPDF TOC used (recursive tree building from levels)
- **Scoped search:** library-wide, group-level, or single-book filtering via SQL WHERE
- **Bedrock-first:** Uses AWS Bedrock if `AWS_BEARER_TOKEN_BEDROCK` set, else direct Anthropic API
- **Dual DB pools:** foreground (8+4 overflow) for UI/API, background (4+2 overflow) for indexing
- **Startup reset:** stuck "processing" books reset to "ready" on app start
- **Embedding batching:** batch size 64, `encode_async` runs in thread pool to avoid blocking event loop
- **Chat tool-use:** Claude decides which tools to call (non-streaming round), then tool results injected into system prompt for streaming answer; page images from `explain_from_book` sent as vision content blocks
- **Chat style:** system prompt instructs conversational prose (no bullet lists, weave citations naturally)
- **MCP explain_from_book:** fuzzy book matching, page-based + semantic retrieval, page images extracted on-the-fly from PDFs (JPEG, 100 DPI, max 2), returned as MCP ImageContent blocks

## Frontend

- **Header** with Bookwise logo + Search nav link
- **Library page** preserves selected group via `?group=` URL param
- **PDF viewer** has chapter sidebar (TOC tree)
- **EPUB navigation** uses chapterId (UUID) matched by title against epub.js TOC
- **EPUB parser:** recursive TOC traversal (`_build_toc_map`) + HTML heading fallback for titles

## Running

```bash
docker-compose up -d          # Start all services
docker-compose exec backend alembic upgrade head  # Apply migrations
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# MCP:      configured in .mcp.json (stdio)
```

## Testing

```bash
cd backend && python -m pytest tests/ -v    # 54+ backend tests (uses books_test DB)
cd frontend && npm test                      # 14 component tests
npx playwright test                          # 7 E2E tests
```

**Important:** Backend tests use `books_test` database (not `books`) to avoid destroying production data.

## Config (.env)

```
DATABASE_URL, BOOKS_STORAGE_PATH, ANTHROPIC_API_KEY,
AWS_BEARER_TOKEN_BEDROCK, AWS_BEDROCK_REGION, BEDROCK_MODEL,
EMBEDDING_MODEL, EMBEDDING_CACHE_PATH, CORS_ORIGINS, FRONTEND_URL
```

## Non-Obvious

- `pgvector` queries use raw SQL (`text()`) — SQLAlchemy doesn't abstract the `<=>` operator
- EPUB "page_count" is actually chapter count (EPUBs have no fixed pages)
- Reindex deletes ALL existing chunks before re-embedding — can take minutes for large books
- Progress tracking is in-memory (ProgressTracker singleton with asyncio.Queue fan-out)
- Chat SSE chunks are JSON-encoded strings; frontend parses `data: "..."` format
- Alembic migrations must be run manually after container rebuild
- Project branded as "Bookwise" (MCP server name, FastAPI title, UI header) but repo folder is still BooksNavigationMCP
- `explain_from_book` strips base64 images from the JSON text block and sends them as separate ImageContent blocks to save space
- Fuzzy book matching uses case-insensitive SQL LIKE containment
