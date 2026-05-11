# Functional Specification: EPUB Support

- **Roadmap Item:** EPUB format support for book ingestion, indexing, and viewing
- **Status:** Completed
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

Many technical books are available in EPUB format alongside or instead of PDF. Currently the system only accepts PDFs, forcing users to find PDF versions or skip EPUB-only books. Adding EPUB support expands the library to cover the user's full book collection.

**Success looks like:** The user uploads an EPUB book using the same workflow as PDFs. The book is parsed, indexed, and searchable. A dedicated EPUB reader in the Web UI renders the book with proper reflowing layout, and search results link directly to the relevant chapter.

---

## 2. Functional Requirements (The "What")

### 2.1. EPUB Upload

- **As a** user, **I want to** upload EPUB books alongside PDFs, **so that** I can index my full book collection regardless of format.
  - **Acceptance Criteria:**
    - [x] The upload zone accepts both PDF and EPUB files.
    - [x] If the user uploads a non-PDF, non-EPUB file, they see "Only PDF and EPUB files are supported."
    - [x] EPUB books are processed through the same ingestion pipeline (metadata extraction, chapter structure, concept indexing).

### 2.2. EPUB Processing

- **As a** user, **I want** EPUB books to be automatically parsed and indexed just like PDFs, **so that** I can search across all my books regardless of format.
  - **Acceptance Criteria:**
    - [x] The system extracts title, author, and chapter structure from the EPUB file.
    - [x] Chapter text is chunked and embedded for semantic search, using the same pipeline as PDFs.
    - [x] The book card shows the same metadata (title, author, page/chapter count, status) as PDFs.

### 2.3. EPUB Viewer

- **As a** user, **I want to** read EPUB books directly in the Web UI with a native reflowing reader, **so that** the reading experience is natural and preserves the EPUB format's advantages.
  - **Acceptance Criteria:**
    - [x] EPUB books open in a dedicated EPUB reader (not the PDF viewer).
    - [x] The reader supports chapter navigation, text reflowing, and zoom/font size controls.
    - [x] Search results for EPUB books link to the reader at the correct chapter.
    - [x] The book detail page shows "View EPUB" instead of "View PDF" for EPUB books.

### 2.4. MCP Integration

- **As a** user, **I want** Claude to search EPUB books the same way it searches PDFs, **so that** format doesn't matter when looking up concepts.
  - **Acceptance Criteria:**
    - [x] MCP `search_books` results for EPUB books include a `viewer_url` that opens the EPUB reader at the right chapter.
    - [x] `get_chapter_content` works for EPUB chapters, returning the chapter text.

---

## 3. Scope and Boundaries

### In-Scope

- Accept EPUB uploads alongside PDF.
- Parse EPUB metadata, TOC, and chapter text using `ebooklib`.
- Index EPUB content with the same embedding pipeline as PDFs.
- Dedicated EPUB viewer in the Web UI using epub.js (or similar).
- MCP search and chapter retrieval for EPUB books.

### Out-of-Scope

- MOBI, AZW, or other ebook formats.
- DRM-protected EPUBs.
- EPUB editing or annotation.
- Converting between PDF and EPUB.
