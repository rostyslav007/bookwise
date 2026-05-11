<!--
This document describes HOW to build the feature at an architectural level.
It is NOT a copy-paste implementation guide.
-->

# Technical Specification: PDF Book Ingestion

- **Functional Specification:** `context/spec/001-pdf-book-ingestion/functional-spec.md`
- **Status:** Completed
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

This feature is the foundational data pipeline for BooksNavigationMCP. It introduces:

- A **FastAPI backend** with REST endpoints for book group management and PDF upload
- A **background processing pipeline** that uses PyMuPDF to extract PDF structure, Claude API for AI-powered TOC generation (fallback), and sentence-transformers for concept embedding
- **SSE (Server-Sent Events)** to push processing progress to the frontend
- A **PostgreSQL database** with pgvector for storing book metadata, chapter structure, and vector embeddings
- A **React frontend** with Tailwind/shadcn for group management, file upload with drag-and-drop, progress tracking, and chapter structure editing

Since this is a greenfield project, this spec also establishes the project scaffolding, Docker Compose setup, and foundational patterns.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Project Structure

**Backend (`backend/`):**

```
backend/
  app/
    main.py                  # FastAPI app factory, lifespan events
    config.py                # Settings via pydantic-settings
    database.py              # SQLAlchemy async engine & session
    routers/
      groups.py              # Group CRUD endpoints
      books.py               # Book upload, list, processing endpoints
      chapters.py            # Chapter structure editing endpoints
      sse.py                 # SSE progress stream endpoint
    services/
      group_service.py       # Group business logic
      book_service.py        # Book upload & catalog logic
      processing_service.py  # PDF parsing, TOC extraction, embedding pipeline
      embedding_service.py   # sentence-transformers wrapper
      claude_service.py      # Claude API for TOC generation
    models/
      group.py               # SQLAlchemy Group model
      book.py                # SQLAlchemy Book model
      chapter.py             # SQLAlchemy Chapter model
      chunk.py               # SQLAlchemy ChunkEmbedding model
    schemas/
      group.py               # Pydantic request/response schemas
      book.py
      chapter.py
  alembic/                   # Database migrations
  requirements.txt
  Dockerfile
```

**Frontend (`frontend/`):**

```
frontend/
  src/
    components/
      groups/                # Group list, create/edit dialog
      books/                 # Upload zone, book card, book list
      chapters/              # Chapter list, edit form
      shared/                # Layout, progress bar, confirmation dialog
    hooks/
      useSSE.ts              # SSE connection hook for progress updates
    api/
      client.ts              # Axios/fetch wrapper
      groups.ts              # TanStack Query hooks for groups
      books.ts               # TanStack Query hooks for books
      chapters.ts            # TanStack Query hooks for chapters
    pages/
      LibraryPage.tsx        # Main page: groups sidebar + book grid
      BookDetailPage.tsx     # Book detail: metadata + chapter list
    App.tsx
    main.tsx
  Dockerfile
  vite.config.ts
```

### 2.2. Data Model / Database Changes

| Table | Key Columns | Notes |
|---|---|---|
| `groups` | `id` (UUID PK), `name` (VARCHAR, unique), `created_at`, `updated_at` | User-created book groups |
| `books` | `id` (UUID PK), `group_id` (FK → groups), `title`, `author`, `file_path`, `page_count`, `status` (enum: uploading/processing/ready/error), `created_at`, `updated_at` | Book metadata; `file_path` points to local PDF storage |
| `chapters` | `id` (UUID PK), `book_id` (FK → books), `parent_id` (FK → chapters, nullable), `title`, `level` (INT), `order` (INT), `start_page`, `end_page`, `created_at` | Hierarchical structure: chapters → sections → sub-sections. `parent_id` enables nesting, `level` indicates depth (0=chapter, 1=section, 2=sub-section). Always AI-enriched. |
| `chunk_embeddings` | `id` (UUID PK), `chapter_id` (FK → chapters), `book_id` (FK → books), `content` (TEXT), `page_number` (INT), `embedding` (VECTOR(384)) | Text chunks with pgvector embeddings for semantic search; 384 dimensions for all-MiniLM-L6-v2 |

**Relationships:**
- `groups` 1:N `books` (cascade delete: warn user, block by default)
- `books` 1:N `chapters` (cascade delete)
- `chapters` 1:N `chunk_embeddings` (cascade delete)
- `books` 1:N `chunk_embeddings` (denormalized FK for efficient book-level queries)

**Migrations:** Managed via Alembic with async SQLAlchemy support.

### 2.3. API Contracts

**Groups:**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/groups` | Create a group `{ name: string }` → `201` with group object |
| `GET` | `/api/v1/groups` | List all groups → `200` with array of group objects |
| `PUT` | `/api/v1/groups/{id}` | Rename a group `{ name: string }` → `200` with updated group |
| `DELETE` | `/api/v1/groups/{id}` | Delete a group → `204` on success, `409` if books exist |

**Books:**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/books` | Upload PDF (multipart/form-data: `file` + `group_id`) → `202` with book object (status: `processing`). Background processing starts immediately. |
| `GET` | `/api/v1/books` | List all books (query param: `group_id` optional) → `200` with array |
| `GET` | `/api/v1/books/{id}` | Get book detail (metadata + chapter count + status) → `200` |
| `GET` | `/api/v1/books/{id}/progress` | SSE stream of processing progress events |

**Chapters:**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/books/{id}/chapters` | List chapters for a book → `200` with ordered array |
| `PUT` | `/api/v1/chapters/{id}` | Update chapter `{ title?, start_page?, end_page? }` → `200` |
| `POST` | `/api/v1/books/{id}/chapters` | Add chapter `{ title, start_page, end_page }` → `201` |
| `DELETE` | `/api/v1/chapters/{id}` | Delete a chapter → `204` |
| `POST` | `/api/v1/chapters/merge` | Merge adjacent chapters `{ chapter_ids: [id1, id2] }` → `200` with merged chapter |
| `POST` | `/api/v1/books/{id}/reindex` | Trigger re-indexing after chapter edits → `202` |

### 2.4. Processing Pipeline

The background processing pipeline runs these steps sequentially after a PDF is uploaded:

1. **Save PDF** → Store file to `data/books/{book_id}.pdf`, emit SSE: `"Uploading..."`
2. **Extract metadata** → PyMuPDF: extract title, author from PDF metadata, emit SSE: `"Extracting metadata..."`
3. **Extract base TOC** → PyMuPDF `doc.get_toc()`. If TOC entries found, use as starting skeleton. If not, AI generates from scratch in step 4. Emit SSE: `"Extracting chapters..."`
4. **AI structure enrichment (always runs)** → Send page text + base TOC (if available) to Claude API. AI generates detailed hierarchical structure: chapters → sections → sub-sections (e.g., "Observer > Intent", "Observer > Motivation"). Creates `chapters` records with `parent_id` and `level` for nesting. Emit SSE: `"Analyzing structure with AI..."`
5. **Chunk text** → Split section text into overlapping chunks (~500 tokens, ~100 token overlap). Emit SSE: `"Indexing concepts..."`
6. **Generate embeddings** → Run chunks through sentence-transformers (all-MiniLM-L6-v2), store vectors in `chunk_embeddings`. Emit SSE: `"Indexing concepts... (X/Y)"`
7. **Mark complete** → Set book status to `ready`. Emit SSE: `"Done"`

On error at any step: set book status to `error`, emit SSE with error message, log details.

### 2.5. Frontend Components

| Component | Responsibility |
|---|---|
| `LibraryPage` | Main view: groups sidebar (list, create, rename, delete) + book grid for selected group |
| `GroupSidebar` | List groups, create new group dialog, rename/delete context menu |
| `BookUploadZone` | Drag-and-drop area + file picker, group selector, upload trigger |
| `BookCard` | Displays book title, author, chapter count, status badge, processing progress bar |
| `BookDetailPage` | Book metadata summary card + editable chapter list |
| `ChapterList` | Sortable list of chapters with inline editing (rename, page range), add/delete/merge actions |
| `ProgressBar` | Real-time progress indicator powered by SSE hook |

**Key libraries:**
- TanStack Query for server state management
- Tailwind CSS + shadcn/ui for styling and components
- React Router for navigation (Library → Book Detail)

### 2.6. Configuration

| Env Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@db:5432/books`) |
| `BOOKS_STORAGE_PATH` | Local directory for PDF file storage (default: `./data/books`) |
| `ANTHROPIC_API_KEY` | Claude API key for AI-powered TOC generation (fallback only) |
| `EMBEDDING_MODEL` | sentence-transformers model name (default: `all-MiniLM-L6-v2`) |
| `CORS_ORIGINS` | Allowed origins for frontend (default: `http://localhost:5173`) |

### 2.7. Docker Compose

Services:
- **backend:** Python 3.12 slim, FastAPI on port 8000, mounts `./data/books` volume
- **frontend:** Node build stage + Nginx, serves SPA on port 3000, proxies `/api` to backend
- **db:** PostgreSQL 16 with pgvector extension, port 5432, persistent volume for data

---

## 3. Impact and Risk Analysis

- **System Dependencies:** This is the first feature — no existing systems are affected. It establishes the foundational patterns that all subsequent features will build on.
- **Potential Risks & Mitigations:**
  - **Large PDF processing time:** Some technical books are 1000+ pages. Mitigation: background processing with SSE progress updates; user is not blocked.
  - **PyMuPDF TOC extraction quality:** Embedded TOCs are often high-level (just chapter titles). Mitigation: AI always enriches into detailed sections/sub-sections regardless of TOC presence.
  - **Claude API cost for structure generation:** Invoked for every book upload but sends page samples, not the full book text. Cost is low for a personal tool with a modest library.
  - **Embedding model memory footprint:** all-MiniLM-L6-v2 is ~80MB. Loads fine in the Docker container with standard memory limits.
  - **Concurrent uploads:** FastAPI BackgroundTasks run in the same process. Multiple simultaneous large uploads may slow processing. Acceptable for a single-user tool.

---

## 4. Testing Strategy

- **Backend unit tests (pytest):** Test services in isolation — group CRUD, PDF metadata extraction, chapter editing logic, embedding generation. Mock external dependencies (Claude API, filesystem).
- **Backend integration tests (pytest + testcontainers):** Test API endpoints against a real PostgreSQL instance via Docker. Verify the full upload → processing → chapter creation flow.
- **Frontend component tests (Vitest + React Testing Library):** Test key interactive components — upload zone behavior, chapter editor CRUD operations, SSE progress display.
- **End-to-end tests (Playwright):** Upload a sample PDF, verify processing completes and progress is shown, verify chapter structure appears, edit a chapter, verify re-indexing triggers.
