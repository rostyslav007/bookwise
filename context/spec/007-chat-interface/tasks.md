# Tasks: Chat Interface

---

## Slice 1: Backend — Scoped Search + Chat Endpoint

_Goal: A streaming chat endpoint that retrieves scoped chunks and streams Claude responses via SSE._

- [x] **Slice 1: Chat backend**
  - [x] Extend `SearchService.search()` with optional `group_id` and `book_id` params to filter chunks by scope. Add WHERE clauses to the SQL query. **[Agent: general-purpose]**
  - [x] Create `ChatService` in `backend/app/services/chat_service.py` with `stream_response()` that retrieves chunks, builds system prompt with context, and streams Claude API response. **[Agent: general-purpose]**
  - [x] Create `POST /api/v1/chat` endpoint in `backend/app/routers/chat.py` that accepts messages + scope + optional group_id/book_id, creates ChatService, and returns SSE streaming response. Register in main.py. **[Agent: general-purpose]**
  - [x] **Verify:** Call the chat endpoint with curl, verify streaming response works with scoped retrieval. **[Agent: general-purpose]**

---

## Slice 2: Frontend — Chat Panel Component

_Goal: A reusable chat panel with message history, streaming responses, and clickable book references._

- [x] **Slice 2: Chat UI**
  - [x] Create `ChatPanel` component with message list (user/assistant bubbles), input bar, send button, and streaming response display. Parse book references in responses as clickable links to PDF/EPUB viewer. **[Agent: general-purpose]**
  - [x] Integrate ChatPanel at three levels: library page (all books), group view (group scope), book detail page (book scope). Add a chat toggle button to show/hide the panel as a right-side drawer. **[Agent: general-purpose]**
  - [x] **Verify:** Open chat at each level, send a message, verify streaming response with book references. Verify scope label shows correctly. **[Agent: general-purpose]**

---

## Slice 3: Tests

_Goal: Test coverage for chat endpoint and scoped search._

- [ ] **Slice 3: Tests**
  - [ ] Add backend tests: scoped search filters correctly by group_id and book_id. Chat endpoint returns streaming response. **[Agent: general-purpose]**
  - [ ] **Verify:** Run `pytest`. All tests pass. **[Agent: general-purpose]**
