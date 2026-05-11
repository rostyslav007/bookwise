# Product Definition: BooksNavigationMCP

- **Version:** 1.0
- **Status:** Proposed

---

## 1. The Big Picture (The "Why")

### 1.1. Project Vision & Purpose

Help a technical professional instantly rediscover concepts from their personal library of technical books. When working on implementation and needing to refresh knowledge about a pattern, architecture, or technique, the product points directly to the exact book, chapter, and page — eliminating the need to search manually or rely solely on web resources.

### 1.2. Target Audience

A solo developer/engineer who actively reads technical books (OOP patterns, infrastructure architecture, system design, etc.) and wants to reference them quickly during coding sessions with Claude.

### 1.3. User Personas

- **Persona 1: "Rostyslav the Engineer"**
  - **Role:** Software engineer who reads technical books regularly.
  - **Goal:** Wants to quickly recall which book and chapter covers a specific concept (e.g., the Strategy pattern, CQRS, event sourcing) and revisit the original text to reinforce understanding.
  - **Frustration:** Has a high-level memory of where concepts live across dozens of books but can't pinpoint the exact chapter or page fast enough. Switching between tools and manually searching PDFs breaks flow.

### 1.4. Success Metrics

- Can ask Claude about a concept and get the exact book + chapter + page reference in under 5 seconds.
- Relevant book content is surfaced first before falling back to Claude's general knowledge.
- The tool is seamlessly available during Claude coding sessions without extra setup or context switching.
- Revisiting source material becomes a regular part of the workflow, reinforcing long-term retention.

---

## 2. The Product Experience (The "What")

### 2.1. Core Features

- **PDF Book Ingestion:** Upload PDF technical books and automatically extract structure (table of contents, chapters, pages) into a searchable index.
- **Concept Search via MCP:** Claude queries the indexed book library by concept, pattern, or topic and receives book + chapter + page references.
- **Chapter Content Retrieval:** Claude can retrieve relevant text chunks from the matched chapters for inline context.
- **In-Browser Book Viewing:** Open the source PDF in Chrome at the exact page where a concept is mentioned, with relevant chunks highlighted.
- **Web UI:** A browser-based interface for the full experience — book management (upload, list, remove), concept search, chapter browsing, reading with highlights, and an integrated PDF viewer.
- **Book Management:** Add, remove, and list books in the personal catalog.
- **Books-First Fallback:** When Claude answers a question, it searches the personal book library first. If the information isn't found there, it falls back to its internal knowledge and other tools — but notifies the user that the answer didn't come from their books.

### 2.2. User Journey

1. The user uploads a technical PDF book to the system (e.g., "Design Patterns" by GoF).
2. The system parses the PDF, extracts the table of contents, chapters, and page structure, and indexes the content by concepts/topics.
3. During a Claude coding session, the user asks: "Where can I read about the Observer pattern?"
4. Claude queries the MCP server, which searches the indexed book library.
5. Claude responds: "The Observer pattern is covered in *Design Patterns* by GoF, Chapter 5, page 293."
6. The user can ask Claude to open the book at that page — Chrome launches with the PDF at the exact page, relevant sections highlighted.
7. If the concept isn't found in any indexed book, Claude falls back to its own knowledge but flags: "Note: this answer is from my general knowledge, not from your book library."

---

## 3. Project Boundaries

### 3.1. What's In-Scope for this Version

- PDF book upload and structural parsing (TOC, chapters, pages).
- Concept/topic indexing and search via MCP tools.
- Chapter content retrieval (relevant text chunks).
- Opening PDFs in Chrome at a specific page with highlighting.
- Web UI with full experience: book management, concept search, chapter browsing, reading with highlights, and PDF viewer.
- Book catalog management (add, remove, list).
- Books-first search with fallback notification.

### 3.2. What's Out-of-Scope (Non-Goals)

- NotebookLM integration (no public API available yet).
- Multi-user support, authentication, or sharing features.
- AI-generated chapter summaries — the goal is to point to the source, not replace it.
- EPUB or other format support (PDF only for v1).
- Mobile application.
