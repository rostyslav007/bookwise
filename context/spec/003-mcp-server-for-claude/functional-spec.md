# Functional Specification: MCP Server for Claude

- **Roadmap Item:** MCP Server for Claude — Concept search, chapter content retrieval, books-first fallback
- **Status:** Completed
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

The user's technical books are now uploaded, parsed, and indexed with vector embeddings. But this knowledge is only accessible through the Web UI. The real value comes when Claude can search the user's book library during coding sessions — answering questions like "Where can I read about the Observer pattern?" with a precise book, chapter, and page reference.

This feature creates an MCP server that Claude Code connects to via stdio. When the user asks about a concept, Claude searches the book library first. If found, it returns exact references and relevant text. If not found, it tells the user the answer comes from general knowledge, not their books.

**Success looks like:** During a coding session, the user asks Claude about a design pattern. Claude searches the book library, finds the match, and responds: "The Observer pattern is covered in *Design Patterns* by GoF, Chapter 5, page 293. Here's the relevant excerpt: ..."

---

## 2. Functional Requirements (The "What")

### 2.1. Concept Search Tool

- **As a** user working with Claude, **I want** Claude to search my book library by concept or topic, **so that** I get pointed to the exact book, chapter, and page where it's discussed.
  - **Acceptance Criteria:**
    - [x] Claude has access to a "search_books" tool that accepts a natural language query (e.g., "Observer pattern", "CQRS architecture", "dependency injection").
    - [x] The tool returns up to 5 results, each containing: book title, author, chapter title, page number, and a relevant text snippet.
    - [x] Results are ranked by relevance using the vector similarity search on the existing embeddings.
    - [x] If no relevant results are found, the tool returns an empty result set with a message indicating no matches were found in the user's library.

### 2.2. Chapter Content Retrieval Tool

- **As a** user, **I want** Claude to retrieve the full content of a specific chapter or section, **so that** I can get detailed context without opening the book manually.
  - **Acceptance Criteria:**
    - [x] Claude has access to a "get_chapter_content" tool that accepts a chapter ID.
    - [x] The tool returns the full text content of the specified chapter, extracted from the PDF.
    - [x] The response includes the chapter title, book title, and page range for reference.

### 2.3. Books-First Fallback

- **As a** user, **I want** to know whether Claude's answer came from my books or from general knowledge, **so that** I can trust the source and decide whether to dive deeper into the book.
  - **Acceptance Criteria:**
    - [x] Each search result includes a "source" field indicating it came from the user's book library (e.g., `"source": "library"`).
    - [x] When no results are found, the response includes `"source": "not_found"` so Claude can inform the user that the answer will come from general knowledge instead.

### 2.4. MCP Server Connection

- **As a** user, **I want** to connect Claude Code to my book library with minimal setup, **so that** the search is available in every coding session.
  - **Acceptance Criteria:**
    - [x] The MCP server runs via stdio transport — Claude Code launches it as a subprocess.
    - [x] The server can be configured in Claude Code's MCP settings (`.mcp.json` or similar) with a simple command.
    - [x] The server connects to the existing PostgreSQL database to access book data and embeddings.

---

## 3. Scope and Boundaries

### In-Scope

- MCP server with stdio transport exposing two tools: `search_books` and `get_chapter_content`.
- Semantic vector search using existing pgvector embeddings.
- Source metadata on search results (`"source": "library"` or `"source": "not_found"`).
- Configuration for Claude Code connection.

### Out-of-Scope

- **In-Browser Book Viewing (open at exact page, highlight chunks)** — separate roadmap item.
- **SSE transport** — stdio only for v1.
- **Web UI search** — Phase 3 roadmap item.
- **Book management via MCP** — use the Web UI for that.
- **Automatic prompt injection** — Claude decides when to use the search tool based on the conversation.
