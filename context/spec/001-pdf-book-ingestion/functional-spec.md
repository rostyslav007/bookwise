# Functional Specification: PDF Book Ingestion

- **Roadmap Item:** PDF Book Ingestion — Upload PDFs, extract structure, and index content by concepts
- **Status:** Completed
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

The user reads many technical books on topics like design patterns, system architecture, and infrastructure. Over time, they build a mental map of where concepts are discussed, but can't quickly pinpoint the exact book, chapter, and page when they need to refresh their knowledge during a coding session.

This feature solves the first part of the problem: getting the books into the system. It allows the user to upload PDF books, organize them into custom groups, and have the system automatically extract the book's structure (chapters, page ranges) and index the content by concepts and topics. This creates the searchable knowledge base that all other features depend on.

**Success looks like:** After uploading a book, the user sees a summary confirming the title, author, chapter count, and group — and knows the book is now searchable by concept.

---

## 2. Functional Requirements (The "What")

### 2.1. Book Groups

- **As a** user, **I want to** create custom groups for organizing my books, **so that** I can categorize them by topic or domain (e.g., "OOP Patterns", "System Design", "Infrastructure").
  - **Acceptance Criteria:**
    - [x] The user can create a new group by entering a name in the Web UI.
    - [x] The user can see a list of all existing groups.
    - [x] The user can rename an existing group.
    - [x] The user can delete a group. If the group contains books, the user is warned before deletion. [NEEDS CLARIFICATION: Should books in a deleted group move to an "Ungrouped" default group, or should deletion be blocked while books exist?]
    - [x] Each book belongs to exactly one group.

### 2.2. PDF Upload

- **As a** user, **I want to** upload a PDF book into a specific group, **so that** it gets processed and becomes part of my searchable library.
  - **Acceptance Criteria:**
    - [x] The user can upload a PDF file via a file picker or drag-and-drop in the Web UI.
    - [x] The user selects which group the book should belong to before or during upload.
    - [x] Only PDF files are accepted. If the user tries to upload a non-PDF file, they see a message: "Only PDF files are supported."
    - [x] There is no file size limit.
    - [x] If a book with the same title already exists in the library, the user is warned before proceeding. [NEEDS CLARIFICATION: Should duplicates be blocked, or allowed with a warning?]

### 2.3. Processing and Structure Extraction

- **As a** user, **I want** the system to automatically extract and enrich the chapter structure from my uploaded book into detailed sections and sub-sections, **so that** search results can point me to the right section and page — not just a whole chapter.
  - **Acceptance Criteria:**
    - [x] After uploading, the user sees a progress indicator with status steps (e.g., "Extracting chapters...", "Analyzing structure with AI...", "Indexing concepts...").
    - [x] The system detects the book's title, author (if available), and basic chapter structure from the PDF.
    - [x] The system always uses AI to enrich the structure into detailed sections and sub-sections (e.g., "Chapter 5: Behavioral Patterns" → "Observer > Intent", "Observer > Motivation", "Observer > Structure").
    - [x] If the book has no recognizable table of contents, the AI generates the entire structure from scratch at the same section/sub-section granularity.
    - [x] Once processing is complete, the user sees a summary card showing: book title, author, number of sections detected, and the group it belongs to.

### 2.4. Chapter Structure Editing

- **As a** user, **I want to** review and edit the extracted chapter structure, **so that** I can correct any mistakes in the automatic extraction.
  - **Acceptance Criteria:**
    - [x] After processing, the user can open the chapter list for any book.
    - [x] The user can rename a chapter.
    - [x] The user can adjust the start and end page of a chapter.
    - [x] The user can add a new chapter (providing a name and page range).
    - [x] The user can delete a chapter.
    - [x] The user can merge two adjacent chapters into one.
    - [x] After editing, the book's concept index is updated to reflect the new structure.

### 2.5. Concept Indexing

- **As a** user, **I want** the content of each chapter to be automatically indexed by concepts and topics, **so that** I can later search across all my books by concept.
  - **Acceptance Criteria:**
    - [x] After a book is uploaded and its structure is extracted, the content is automatically indexed by concepts, patterns, and topics.
    - [x] The indexing happens as part of the processing pipeline — no separate action is needed from the user.
    - [x] Concept indexing works behind the scenes — the user does not see or manage individual concept tags.
    - [x] If the chapter structure is edited, the concept index is automatically refreshed.

---

## 3. Scope and Boundaries

### In-Scope

- Creating, renaming, and deleting book groups via the Web UI.
- Uploading PDF books into a specific group via the Web UI.
- Automatic extraction of book title, author, and chapter structure from uploaded PDFs.
- AI-powered chapter structure generation for books without a recognizable table of contents.
- Progress indicator during book processing.
- Summary card after successful processing.
- Editing the extracted chapter structure (rename, add, delete, merge chapters, adjust page ranges).
- Automatic concept indexing of book content (behind the scenes).
- Re-indexing after chapter structure edits.

### Out-of-Scope

- **Book Catalog Management (listing, removing books)** — separate roadmap item.
- **MCP Server for Claude (concept search, chapter content retrieval, books-first fallback)** — Phase 2 roadmap item.
- **In-Browser Book Viewing (open at exact page, highlight chunks)** — Phase 2 roadmap item.
- **Web UI search and reading experience (concept search, chapter browser, integrated PDF viewer)** — Phase 3 roadmap item.
- EPUB or other non-PDF formats.
- Multi-user support or authentication.
- AI-generated chapter summaries.
