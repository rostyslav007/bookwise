# BooksNavigationMCP

Personal technical book RAG system — upload PDF/EPUB books, index with vector embeddings, search via semantic similarity, chat with Claude about your library.

## Stack

- **Backend:** Python 3.12 FastAPI + PostgreSQL/pgvector + PyMuPDF + ebooklib
- **Frontend:** React 19 + TypeScript + Vite + Tailwind/shadcn + react-pdf + epubjs
- **MCP Server:** Python MCP SDK (stdio) — `search_books` + `get_chapter_content`
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384-dim, local)
- **Chat:** Claude Sonnet via AWS Bedrock (configurable, falls back to direct Anthropic API)
- **Deployment:** Docker Compose (backend:8000, frontend:3000, postgres:5432)

## Architecture

```
Upload PDF/EPUB → Extract metadata + TOC → AI structure enrichment (optional)
→ Save chapters (hierarchical) → Chunk text (heading-based or fixed)
→ Embed with sentence-transformers → Store in pgvector

Search query → Embed → Cosine similarity → Ranked results with viewer_url
Chat → RAG retrieval (scoped) → Claude streaming response with book citations
```

## Key Patterns

- **Lazy singleton** for EmbeddingService — loaded once, reused globally
- **SSE streaming** for processing progress + chat responses
- **Dual chunking:** "headings" (font-size heuristic for PDF, h1/h2/h3 for EPUB) or "fixed" (2000 chars / 400 overlap)
- **AI fallback:** Claude structure generation fails → raw PyMuPDF TOC used
- **Scoped search:** library-wide, group-level, or single-book filtering via SQL WHERE
- **Bedrock-first:** Uses AWS Bedrock if `AWS_BEARER_TOKEN_BEDROCK` set, else direct Anthropic API

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
EMBEDDING_MODEL, CORS_ORIGINS, FRONTEND_URL
```

## Non-Obvious

- `pgvector` queries use raw SQL (`text()`) — SQLAlchemy doesn't abstract the `<=>` operator
- EPUB "page_count" is actually chapter count (EPUBs have no fixed pages)
- Reindex deletes ALL existing chunks before re-embedding — can take minutes for large books
- Progress tracking is in-memory (ProgressTracker singleton with asyncio.Queue fan-out)
- Chat SSE chunks are JSON-encoded strings; frontend parses `data: "..."` format
- Alembic migrations must be run manually after container rebuild
