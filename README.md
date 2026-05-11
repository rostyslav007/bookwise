# Bookwise

Personal technical book library with semantic search, RAG chat, and built-in readers -- designed for engineers who learn from books and want that knowledge accessible during coding.

Inspired by [Google NotebookLM](https://notebooklm.google.com/), but self-hosted, API-first, and built for deep navigation rather than summaries.

## Why not NotebookLM?

NotebookLM is great for quick AI-powered summaries and audio overviews, but it falls short for technical book workflows:

| | **Bookwise** | **NotebookLM** |
|---|---|---|
| **Book viewer** | Built-in PDF/EPUB reader with page navigation, zoom, and keyword highlighting | No viewer -- AI citations only, click to see source snippets |
| **Cross-library search** | Semantic search across your entire library, scoped by group or book | Notebooks are isolated silos, no cross-notebook search |
| **API access** | Full REST API (FastAPI) for programmatic access | No public API (enterprise-only, pre-GA) |
| **MCP server** | Native MCP support -- Claude can search your books during coding sessions | No official MCP -- only community workarounds via browser automation |
| **Self-hosted** | Runs locally via Docker Compose, your data stays on your machine | Cloud-only (Google-hosted) |
| **Integration** | Connect to Obsidian, Claude Code, or any MCP-compatible tool | Manual export/import only, no bidirectional integrations |
| **Navigation** | Jump to exact page/chapter from search results or chat citations | Limited to AI-generated citation links within a single notebook |

Bookwise trades NotebookLM's audio overviews and polished UX for **ownership, programmability, and deep navigation** across your technical library.

## Features

- **Upload PDF/EPUB** -- automatic metadata extraction, TOC parsing, and AI-powered chapter structure generation
- **Semantic search** -- vector similarity search (pgvector) across your entire library with ranked results
- **RAG chat** -- streaming chat with Claude, grounded in your books with clickable citations that open the exact page
- **Built-in viewers** -- PDF viewer (react-pdf) with page nav, zoom, and highlight; EPUB viewer (epubjs) with chapter TOC
- **Book organization** -- group books by topic, search within groups or across the whole library
- **MCP server** -- expose your library to Claude Code, Cursor, or any MCP-compatible AI assistant
- **REST API** -- full CRUD for books, chapters, groups, search, and chat

## Architecture

```
Upload PDF/EPUB --> Extract metadata + TOC --> AI structure enrichment
--> Save chapters (hierarchical) --> Chunk text (heading-based or fixed)
--> Embed with sentence-transformers --> Store in pgvector

Search query --> Embed --> Cosine similarity --> Ranked results with viewer links
Chat --> RAG retrieval (scoped) --> Claude streaming response with book citations
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL + pgvector
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, react-pdf, epubjs
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384-dim, runs locally)
- **Chat:** Claude Sonnet via AWS Bedrock (falls back to direct Anthropic API)
- **MCP Server:** Python MCP SDK (stdio transport)
- **Deployment:** Docker Compose

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2+
- [uv](https://docs.astral.sh/uv/) (Python package manager) -- for running the MCP server locally
- AWS Bedrock access with a valid bearer token (for chat and AI structure generation), or an Anthropic API key as fallback
- ~2 GB disk space for the embedding model (downloaded on first run)

### Run

```bash
git clone <repo-url> && cd bookwise

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Apply database migrations
docker-compose exec backend alembic upgrade head
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `BOOKS_STORAGE_PATH` | Local directory for uploaded books | Yes |
| `AWS_BEARER_TOKEN_BEDROCK` | AWS Bedrock token (primary chat provider) | Yes |
| `AWS_BEDROCK_REGION` | Bedrock region (default: `us-east-1`) | No |
| `BEDROCK_MODEL` | Bedrock model ID | No |
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback if Bedrock not set) | No |
| `EMBEDDING_MODEL` | Sentence-transformers model (default: `all-MiniLM-L6-v2`) | No |
| `CORS_ORIGINS` | Allowed frontend origins | No |

Bedrock is the primary chat provider. `ANTHROPIC_API_KEY` is only used as a fallback if Bedrock is not configured. If neither key is valid, interactive chat won't work -- but book upload, semantic search, navigation, and the built-in viewers remain fully functional.

## MCP Server

Bookwise exposes two tools via MCP for use with Claude Code, Cursor, or other MCP-compatible assistants:

- **`search_books(query)`** -- semantic search across your library, returns book title, chapter, page number, and text snippet
- **`get_chapter_content(chapter_id)`** -- retrieve full chapter text with metadata

### Configure in Claude Code

Add to your `.mcp.json`:

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

### Use Cases

- **During coding:** ask Claude "how does the Observer pattern work?" and get answers grounded in your books
- **Obsidian integration:** use the API to pull book excerpts into your notes
- **Learning workflows:** search concepts across multiple books, jump to the relevant page, and read in context

## Testing

```bash
# Backend (uses books_test database)
cd backend && python -m pytest tests/ -v

# Frontend component tests
cd frontend && npm test

# E2E tests (Playwright)
npx playwright test
```

## License

MIT
