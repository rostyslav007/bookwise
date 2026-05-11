# Tasks: Book Catalog Management

---

## Slice 1: Delete Book + Group Cascade

_Goal: User can delete any book (with full cleanup) and delete groups that contain books (cascade). All data and PDF files are removed._

- [x] **Slice 1: Book delete and group cascade delete**
  - [x] Add Alembic migration to alter `books.group_id` FK with `ON DELETE CASCADE`. Update `Book` model to match. **[Agent: general-purpose]**
  - [x] Add `delete` method to `BookService`: look up book (404 if not found), delete PDF file from disk, delete book record. Add `DELETE /api/v1/books/{book_id}` endpoint (204). **[Agent: general-purpose]**
  - [x] Update `GroupService.delete`: before deleting the group, query all books in the group and delete their PDF files from disk. The group + books + chapters + chunks cascade via FK. **[Agent: general-purpose]**
  - [x] Add `useDeleteBook()` mutation hook to `frontend/src/api/books.ts`. Add "Delete book" button with AlertDialog confirmation to `BookDetailPage`. On confirm, navigate to `/`. **[Agent: general-purpose]**
  - [x] Update group delete confirmation in `GroupSidebar`: warn that all books in the group will also be deleted. **[Agent: general-purpose]**
  - [x] **Verify:** Delete a book from its detail page — verify book, chapters, chunks removed from DB and PDF removed from disk. Delete a group with books — verify group, books, and files are all removed. **[Agent: general-purpose]**

---

## Slice 2: Tests

_Goal: Test coverage for delete operations._

- [x] **Slice 2: Backend + E2E tests for delete**
  - [x] Add backend tests: book delete (verify record + file removed), group cascade delete (verify books + files removed). **[Agent: general-purpose]**
  - [x] Add Playwright E2E test: navigate to book detail, delete book, verify redirect to library and book is gone. **[Agent: general-purpose]**
  - [x] **Verify:** Run `pytest` and `playwright test`. All tests pass. **[Agent: general-purpose]**
