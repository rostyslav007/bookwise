<!--
This document describes HOW to build the feature at an architectural level.
-->

# Technical Specification: Chat Interface

- **Functional Specification:** `context/spec/007-chat-interface/functional-spec.md`
- **Status:** Draft
- **Author(s):** Poe

---

## 1. High-Level Technical Approach

1. **Backend:** A streaming chat endpoint (`POST /api/v1/chat`) that:
   - Accepts a message + conversation history + scope (all/group/book)
   - Retrieves relevant chunks via `SearchService` (extended with scope filters)
   - Builds a prompt with retrieved context + conversation history
   - Streams Claude API response via SSE

2. **Frontend:** A chat panel component that can be embedded at three levels:
   - Library page (scope: all)
   - Group view (scope: group_id)
   - Book detail page (scope: book_id)

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1. Backend: Extend SearchService with Scope Filters

**File:** `backend/app/services/search_service.py`

Add a `search_scoped` method (or add optional params to existing `search`):

| Param | Type | Description |
|---|---|---|
| `query` | str | User's question |
| `limit` | int | Number of chunks (default 10) |
| `group_id` | UUID \| None | Filter to group's books only |
| `book_id` | UUID \| None | Filter to single book only |

The SQL WHERE clause adds:
- `AND b.group_id = :group_id` when group_id is set
- `AND ce.book_id = :book_id` when book_id is set

### 2.2. Backend: Chat Service

**File:** `backend/app/services/chat_service.py`

```python
class ChatService:
    def __init__(self, search_service: SearchService, api_key: str) -> None:
        self._search = search_service
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def stream_response(
        self,
        messages: list[dict],  # conversation history [{role, content}, ...]
        scope_label: str,
        group_id: UUID | None = None,
        book_id: UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        # 1. Extract the latest user message for RAG retrieval
        latest_query = messages[-1]["content"]

        # 2. Retrieve relevant chunks
        results = await self._search.search(
            latest_query, limit=15, group_id=group_id, book_id=book_id
        )

        # 3. Build system prompt with context
        context_text = self._format_context(results)
        system_prompt = f"""You are a helpful assistant discussing technical books.
Scope: {scope_label}

Use the following book excerpts to answer the user's question.
When citing, include the book title, chapter, and page number.
If the excerpts don't contain relevant information, say so and answer from general knowledge.

---
{context_text}
---"""

        # 4. Stream Claude response
        async with self._client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

### 2.3. Backend: Chat Endpoint

**File:** `backend/app/routers/chat.py`

```
POST /api/v1/chat
Body: {
    messages: [{role: "user"|"assistant", content: str}],
    scope: "library" | "group" | "book",
    group_id?: str,
    book_id?: str
}
Response: SSE stream of text chunks
```

Uses `StreamingResponse` with `text/event-stream` for real-time streaming.

Register in `main.py`.

### 2.4. Frontend: Chat Component

**File:** `frontend/src/components/chat/ChatPanel.tsx`

Props: `scope: "library" | "group" | "book"`, `groupId?: string`, `bookId?: string`, `scopeLabel: string`

- Message list with user/assistant bubbles
- Input bar at bottom with send button
- Streams response using `fetch` with `ReadableStream` reader
- References in Claude's response are rendered as clickable links (parse `[Book Title, Chapter X, p.123]` patterns and link to viewer)

### 2.5. Frontend: Integration at Three Levels

- **LibraryPage:** Add a chat toggle button. When active, show `ChatPanel` with `scope="library"`
- **LibraryPage (group selected):** Show `ChatPanel` with `scope="group"` and `groupId`
- **BookDetailPage:** Show `ChatPanel` with `scope="book"` and `bookId`

The chat panel can be a sliding drawer or a split-panel on the right side of the page.

---

## 3. Impact and Risk Analysis

- **System Dependencies:** Uses the existing Claude API key (same as TOC generation). Adds `anthropic` streaming in the backend.
- **Potential Risks:**
  - **Claude API cost:** Each chat message triggers a Claude API call with context. Mitigated by using Sonnet (cheaper than Opus) and limiting context to 10-20 chunks.
  - **Context window:** 10-20 chunks of ~2000 chars each = ~20-40K chars of context. Well within Claude's limits.
  - **Streaming through Nginx:** Already configured for SSE from the progress tracking feature.

---

## 4. Testing Strategy

- **Backend:** Test chat endpoint returns streaming response. Test scoped search filters correctly.
- **Frontend:** Test ChatPanel renders messages and handles streaming.
