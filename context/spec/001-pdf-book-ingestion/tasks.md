# Tasks: PDF Book Ingestion

---

## Slice 1: Project Scaffolding & Docker Compose

_Goal: A running application stack — backend returns a health check, frontend loads a blank page, database is accessible._

- [x] **Slice 1: Project scaffolding with Docker Compose**
  - [x] Create `backend/` project structure: `app/main.py` with FastAPI app, health check endpoint (`GET /api/v1/health`), `requirements.txt` with core dependencies (fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic-settings), and `Dockerfile` (Python 3.12 slim). **[Agent: python-backend]**
  - [x] Create `backend/app/config.py` with pydantic-settings for `DATABASE_URL`, `BOOKS_STORAGE_PATH`, `ANTHROPIC_API_KEY`, `EMBEDDING_MODEL`, `CORS_ORIGINS`. **[Agent: python-backend]**
  - [x] Create `frontend/` project: scaffold React + Vite + TypeScript app, install Tailwind CSS + shadcn/ui, TanStack Query, React Router. Create a minimal `App.tsx` with a "BooksNavigationMCP" heading. Create `Dockerfile` (Node build + Nginx). **[Agent: react-frontend]**
  - [x] Create `docker-compose.yml` with three services: `backend` (port 8000), `frontend` (port 3000, Nginx proxies `/api` to backend), `db` (PostgreSQL 16 + pgvector, port 5432, persistent volume). Add `.env.example`. **[Agent: docker-infra]**
  - [x] Create Alembic configuration with async SQLAlchemy support. Create `backend/app/database.py` with async engine and session factory. **[Agent: python-backend]**
  - [x] **Verify:** Run `docker-compose up`. Confirm backend health check responds at `http://localhost:8000/api/v1/health`, frontend loads at `http://localhost:3000`, database accepts connections. **[Agent: general-purpose]**

---

## Slice 2: Book Groups CRUD

_Goal: User can create, view, rename, and delete book groups via the Web UI._

- [x] **Slice 2: Book groups — backend + frontend end-to-end**
  - [x] Create `groups` table migration (id UUID, name VARCHAR unique, created_at, updated_at). Create SQLAlchemy `Group` model and Pydantic schemas. **[Agent: postgres-database]**
  - [x] Create `GroupService` with CRUD operations. Create `routers/groups.py` with endpoints: `POST /api/v1/groups`, `GET /api/v1/groups`, `PUT /api/v1/groups/{id}`, `DELETE /api/v1/groups/{id}` (returns 409 if books exist). **[Agent: python-backend]**
  - [x] Create `GroupSidebar` component: list all groups, "New Group" button with name input dialog, rename/delete via context menu. Create `LibraryPage` with sidebar layout. Set up TanStack Query hooks for groups API. **[Agent: react-frontend]**
  - [x] **Verify:** Run the app. Use the browser to create a group "OOP Patterns", rename it to "Design Patterns", create a second group "System Design", delete "System Design". Verify all operations persist after page refresh. **[Agent: general-purpose]**

---

## Slice 3: PDF Upload & File Storage

_Goal: User can upload a PDF into a group and see it appear in the book list with "processing" status._

- [x] **Slice 3: PDF upload with file storage**
  - [x] Create `books` table migration (id UUID, group_id FK, title, author, file_path, page_count, status enum, created_at, updated_at). Create SQLAlchemy `Book` model and Pydantic schemas. **[Agent: postgres-database]**
  - [x] Create `BookService` with upload logic: accept multipart file, validate PDF mimetype, save file to `data/books/{book_id}.pdf`, create book record with status `processing`. Create `routers/books.py` with `POST /api/v1/books` (multipart), `GET /api/v1/books` (filter by group_id), `GET /api/v1/books/{id}`. **[Agent: python-backend]**
  - [x] Create `BookUploadZone` component with drag-and-drop + file picker, group selector. Create `BookCard` component showing title, status badge. Create `BookGrid` within `LibraryPage` showing books for selected group. Set up TanStack Query hooks for books API. **[Agent: react-frontend]**
  - [x] **Verify:** Upload a sample PDF into "Design Patterns" group. Verify the book appears in the grid with "processing" status. Verify the PDF file is saved on disk. Verify non-PDF files are rejected with an error message. **[Agent: general-purpose]**

---

## Slice 4: PDF Parsing & AI-Enriched Structure Extraction

_Goal: After upload, the system extracts metadata, uses the embedded TOC as a skeleton (if available), and always runs AI to generate a detailed hierarchical structure (chapters → sections → sub-sections). Book status changes to "ready"._

- [x] **Slice 4: PDF processing pipeline — metadata, TOC extraction, and AI structure enrichment**
  - [x] Create `chapters` table migration (id UUID, book_id FK, parent_id FK nullable self-referencing, title, level INT, order INT, start_page, end_page, created_at). Create SQLAlchemy `Chapter` model with self-referential relationship for hierarchy. **[Agent: postgres-database]**
  - [x] Add PyMuPDF (`pymupdf`) to requirements. Create `ProcessingService` with: extract metadata (title, author from PDF info), extract base TOC via `doc.get_toc()` as a starting skeleton. **[Agent: python-backend]**
  - [x] Add `anthropic` SDK to requirements. Create `ClaudeService` that accepts page text samples + base TOC (if available) and returns a detailed hierarchical structure: chapters → sections → sub-sections (e.g., "Observer > Intent", "Observer > Motivation", "Observer > Structure"). **[Agent: python-backend]**
  - [x] Integrate `ClaudeService` into `ProcessingService`: AI enrichment always runs. If base TOC exists, AI uses it as skeleton and breaks each chapter into named sections/sub-sections. If no TOC, AI generates the entire structure from scratch. Create hierarchical `chapters` records with `parent_id` and `level`. **[Agent: python-backend]**
  - [x] Wire processing as a FastAPI `BackgroundTask` triggered after upload in `POST /api/v1/books`. Update book status to `ready` on success or `error` on failure. Update `page_count` from PDF metadata. **[Agent: python-backend]**
  - [x] Create `GET /api/v1/books/{id}/chapters` endpoint returning hierarchical chapter tree. **[Agent: python-backend]**
  - [x] Update `BookCard` to show author, section count, and page count when status is `ready`. Add polling or manual refresh to detect status change. **[Agent: react-frontend]**
  - [x] **Verify:** Upload a PDF with an embedded TOC. Verify status transitions to "ready". Verify chapters are enriched with sub-sections (not just flat chapter titles). Upload a PDF without TOC. Verify AI generates the full structure from scratch. Verify book card shows metadata. **[Agent: general-purpose]**

---

## Slice 5: SSE Progress Updates

_Goal: User sees real-time processing progress during PDF upload and parsing._

- [x] **Slice 5: Server-Sent Events for processing progress**
  - [x] Implement SSE progress tracking in `ProcessingService`: emit events at each pipeline step ("Uploading...", "Extracting metadata...", "Extracting chapters...", "Analyzing structure with AI...", "Indexing concepts...", "Done"). Create `routers/sse.py` with `GET /api/v1/books/{id}/progress` SSE endpoint. **[Agent: python-backend]**
  - [x] Create `useSSE` hook for EventSource connection. Create `ProgressBar` component showing current processing step. Integrate into `BookCard` — show progress bar when status is `processing`. **[Agent: react-frontend]**
  - [x] **Verify:** Upload a new PDF. Verify the progress bar shows each step in real-time, including "Analyzing structure with AI...". Verify the progress bar disappears and the book card updates when processing completes. **[Agent: general-purpose]**

---

## Slice 6: Concept Embedding & Indexing

_Goal: Book content is chunked and embedded for semantic search. This completes the ingestion pipeline._

- [x] **Slice 6: Text chunking and vector embedding**
  - [x] Create `chunk_embeddings` table migration (id UUID, chapter_id FK, book_id FK, content TEXT, page_number INT, embedding VECTOR(384)). Create SQLAlchemy `ChunkEmbedding` model. **[Agent: postgres-database]**
  - [x] Add `sentence-transformers` to requirements. Create `EmbeddingService` that loads `all-MiniLM-L6-v2`, accepts text chunks, returns embeddings. **[Agent: python-backend]**
  - [x] Add chunking logic to `ProcessingService`: split section text into ~500 token chunks with ~100 token overlap. Generate embeddings via `EmbeddingService`. Store chunks + embeddings in `chunk_embeddings`. Update SSE progress with chunk count. **[Agent: python-backend]**
  - [x] **Verify:** Upload a PDF. After processing completes, query the database to confirm `chunk_embeddings` records exist with non-null embedding vectors. Verify SSE showed "Indexing concepts... (X/Y)" progress. **[Agent: general-purpose]**

---

## Slice 7: Chapter Structure Editing

_Goal: User can view, rename, add, delete, and merge sections for any book, with re-indexing on edit._

- [x] **Slice 7: Chapter/section editing and re-indexing**
  - [x] Create chapter editing endpoints: `PUT /api/v1/chapters/{id}`, `POST /api/v1/books/{id}/chapters`, `DELETE /api/v1/chapters/{id}`, `POST /api/v1/chapters/merge`, `POST /api/v1/books/{id}/reindex`. Implement re-indexing logic: delete existing chunks for affected chapters, re-chunk and re-embed. All endpoints support hierarchical structure (parent_id, level). **[Agent: python-backend]**
  - [x] Create `BookDetailPage` with book metadata summary card and `ChapterList` component. `ChapterList` shows hierarchical tree (chapters → sections → sub-sections) with inline editing (rename, page range adjustment), add/delete/merge actions. Set up TanStack Query hooks for chapter endpoints. Add navigation from `BookCard` to `BookDetailPage`. **[Agent: react-frontend]**
  - [x] **Verify:** Navigate to a book's detail page. Verify hierarchical structure is displayed (chapters with nested sections). Rename a section. Add a new section under a chapter. Delete a section. Merge two adjacent sections. Verify all changes persist. Verify re-indexing runs after edits. **[Agent: general-purpose]**

---

## Slice 8: Backend Tests

_Goal: Comprehensive test coverage for all backend services and endpoints._

- [x] **Slice 8: Backend test suite**
  - [x] Add test dependencies (pytest, pytest-asyncio, httpx, testcontainers). Create test fixtures for database, app client, and sample PDF files. **[Agent: python-backend]**
  - [x] Write unit tests for `GroupService`, `BookService`, `ProcessingService` (mock Claude API and filesystem). Write integration tests for all API endpoints against a real PostgreSQL container. **[Agent: python-backend]**
  - [x] **Verify:** Run `pytest` inside the backend container. All tests pass. **[Agent: general-purpose]**

---

## Slice 9: Frontend Tests & E2E

_Goal: Component tests and end-to-end test coverage._

- [x] **Slice 9: Frontend and E2E tests**
  - [x] Add Vitest + React Testing Library. Write component tests for `BookUploadZone` (file validation, drag-and-drop), `ChapterList` (hierarchical CRUD operations), `GroupSidebar` (create/rename/delete). **[Agent: react-frontend]**
  - [x] Write Playwright E2E test: create a group, upload a PDF, wait for processing, verify hierarchical section structure, edit a section, verify re-indexing. **[Agent: general-purpose]**
  - [x] **Verify:** Run `vitest` for component tests, `playwright test` for E2E. All tests pass. **[Agent: general-purpose]**
