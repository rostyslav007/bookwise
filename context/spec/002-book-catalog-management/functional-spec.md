# Functional Specification: Book Catalog Management

- **Roadmap Item:** Book Catalog Management — Manage the personal book library, add and remove books
- **Status:** Completed
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

The user has uploaded books but currently cannot remove them or delete groups that contain books. This creates dead data and clutter. Book Catalog Management completes the lifecycle by enabling full control over the library — users can remove books they no longer need (cleaning up all associated data and files) and delete groups even when they contain books.

**Success looks like:** The user can freely manage their library — delete any book or group without restrictions, with clear warnings before destructive actions.

---

## 2. Functional Requirements (The "What")

### 2.1. Delete a Book

- **As a** user, **I want to** remove a book from my library, **so that** I can clean up books I no longer need.
  - **Acceptance Criteria:**
    - [x] On the book detail page, there is a "Delete book" button.
    - [x] Clicking "Delete book" shows a confirmation dialog warning that the book, its chapter structure, search index, and PDF file will be permanently removed.
    - [x] After confirming, the book and all its associated data are removed, and the user is returned to the library page.
    - [x] The PDF file is also deleted from disk.

### 2.2. Delete a Group with Books (Cascade)

- **As a** user, **I want to** delete a group even when it contains books, **so that** I can reorganize my library without having to manually empty groups first.
  - **Acceptance Criteria:**
    - [x] When deleting a group that contains books, the confirmation dialog warns the user that all books in the group will also be permanently deleted.
    - [x] After confirming, the group and all its books (including chapters, search index, and PDF files) are removed.

### 2.3. List Books with Metadata

- **As a** user, **I want to** see all my books with their metadata, **so that** I can browse my library at a glance.
  - **Acceptance Criteria:**
    - [x] Each book in the library shows its title, author (if available), page count, and processing status.
    - [x] Books are listed within their group when a group is selected in the sidebar.

---

## 3. Scope and Boundaries

### In-Scope

- Delete a book from the book detail page (removes record, chapters, embeddings, and PDF file).
- Cascade delete when removing a group with books.
- Confirmation dialogs with clear warnings for destructive actions.
- Book listing with metadata (already partially implemented).

### Out-of-Scope

- **MCP Server for Claude** — Phase 2 roadmap item.
- **In-Browser Book Viewing** — Phase 2 roadmap item.
- **Web UI search and reading experience** — Phase 3 roadmap item.
- Moving books between groups.
- Searching/filtering books by title.
- Sorting books.
