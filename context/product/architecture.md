# System Architecture Overview: BooksNavigationMCP

---

## 1. Application & Technology Stack

- **Backend Framework:** Python 3.12+ with FastAPI — async API server, MCP server host, PDF processing pipeline
- **Frontend Framework:** React with Vite — single-page application for the Web UI
- **MCP Protocol:** Python MCP SDK — exposes book search tools to Claude Code / Claude Desktop
- **PDF Parsing:** PyMuPDF (fitz) — text extraction, TOC parsing, page-level control, annotation support

---

## 2. Data & Persistence

- **Primary Database:** PostgreSQL with pgvector extension — stores book metadata, chapter structure, concept index, and vector embeddings for semantic search
- **Embedding Model:** sentence-transformers (all-MiniLM-L6-v2) — runs locally, generates vector embeddings for concept indexing at zero cost
- **File Storage:** Local filesystem — uploaded PDF books stored in a dedicated directory on disk

---

## 3. Infrastructure & Deployment

- **Container Orchestration:** Docker Compose — runs all services (FastAPI backend, PostgreSQL, React frontend) as a single stack
- **Backend Container:** Python 3.12 slim image with FastAPI, PyMuPDF, sentence-transformers
- **Database Container:** PostgreSQL 16 with pgvector extension
- **Frontend Container:** Node-based build stage + Nginx for serving the React SPA

---

## 4. External Services & APIs

- **Authentication:** None — personal single-user tool, no auth required
- **External APIs:** None — fully self-contained, no third-party API dependencies
- **MCP Integration:** Claude Code / Claude Desktop connects to the MCP server via stdio or SSE transport

---

## 5. Observability & Monitoring

- **Logging:** Python standard logging to stdout — viewable via `docker-compose logs`
- **Health Checks:** Docker Compose health checks for service readiness
- **Error Tracking:** Application-level error logging to stdout/stderr
