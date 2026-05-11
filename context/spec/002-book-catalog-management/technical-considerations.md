<!--
This document describes HOW to build the feature at an architectural level.
-->

# Technical Specification: Book Catalog Management

- **Functional Specification:** `context/spec/002-book-catalog-management/functional-spec.md`
- **Status:** Completed
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

This is a small feature that modifies existing backend services and frontend components — no new tables, models, or services are needed. The changes are:

1. **Add a book delete endpoint** that removes the book record (chapters and embeddings cascade via FK), and deletes the PDF file from disk.
2. **Fix group deletion** to cascade through books — delete all books (and their files) in a group before deleting the group itself, since the `books.group_id` FK lacks an `ondelete` clause.
3. **Add delete UI** to the BookDetailPage and update the group delete confirmation dialog.

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Backend: Book Delete

**File:** `backend/app/services/book_service.py`

Add a `delete` method to `BookService`:
- Look up the book by ID (404 if not found)
- Delete the PDF file from disk using `Path.unlink(missing_ok=True)`
- Delete the book record (chapters and chunk_embeddings cascade via existing FK `ondelete="CASCADE"`)

**File:** `backend/app/routers/books.py`

Add endpoint: `DELETE /api/v1/books/{book_id}` → 204 No Content

### 2.2. Backend: Group Cascade Delete

**File:** `backend/app/services/group_service.py`

Update the `delete` method:
- Before deleting the group, query all books in the group
- For each book, delete its PDF file from disk
- Delete the group (need to handle the FK constraint — either add a migration to set `ondelete="CASCADE"` on `books.group_id`, or delete books in the service before deleting the group)

**Recommended approach:** Add an Alembic migration to set `ondelete="CASCADE"` on the `books.group_id` FK, and also update the model. This way SQLAlchemy handles the cascade automatically for chapters/chunks. The service only needs to handle file deletion.

**File:** `backend/app/models/book.py`

Update FK: `ForeignKey("groups.id", ondelete="CASCADE")`

**Migration:** Alter the FK constraint on `books.group_id` to add `ON DELETE CASCADE`.

### 2.3. Frontend: Delete Book Button

**File:** `frontend/src/api/books.ts`

Add `useDeleteBook()` mutation hook for `DELETE /api/v1/books/{id}`.

**File:** `frontend/src/pages/BookDetailPage.tsx`

Add a "Delete book" button (red/destructive styling) with an AlertDialog confirmation:
- Warning text: "This will permanently delete the book, its chapter structure, search index, and PDF file."
- On confirm: call delete mutation, then navigate to `/` (library page).

### 2.4. Frontend: Update Group Delete Dialog

**File:** `frontend/src/components/groups/GroupSidebar.tsx`

Update the group delete confirmation dialog:
- Before showing the dialog, check if the group has books (use the books query or add a book count to the groups API)
- If the group has books, show a stronger warning: "This will also permanently delete all X books in this group, including their data and PDF files."
- If empty, show the current simple warning.

**Simpler alternative:** Always show the cascade warning text regardless. Since it's a personal tool, the extra check isn't critical.

---

## 3. Impact and Risk Analysis

- **System Dependencies:** Chapters and chunk_embeddings already cascade from books via FK. The only gap is `books.group_id` which needs the cascade added.
- **Potential Risks & Mitigations:**
  - **Orphaned PDF files:** If the database delete succeeds but file deletion fails, orphaned files remain on disk. Mitigation: delete file first, then database record. If file deletion fails, log a warning but proceed with the database delete (the file is useless without the record).
  - **Migration on existing data:** Adding `ON DELETE CASCADE` to an existing FK is safe — it only changes behavior on future deletes.

---

## 4. Testing Strategy

- **Backend tests:** Add tests for book delete (verify record + file removed), group cascade delete (verify books + files removed).
- **Frontend:** Existing E2E tests cover group delete. Add a test for book delete flow.
