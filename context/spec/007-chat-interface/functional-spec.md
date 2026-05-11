# Functional Specification: Chat Interface

- **Roadmap Item:** AI chat over book library at three scope levels
- **Status:** Draft
- **Author:** Poe

---

## 1. Overview and Rationale (The "Why")

The user can search their book library via the search page or MCP, but both are single-query interactions. A conversational chat lets the user have multi-turn discussions with Claude about their books — asking follow-up questions, drilling into specific concepts, and getting Claude to point to exact sections. Three scope levels let the user choose how broad or narrow the conversation context should be.

**Success looks like:** The user opens a chat on a specific book and asks "Explain the differences between narrow and wide transformations" — Claude answers using the book's content, cites the exact chapter and page, and the user can follow up with "Show me the code example for this."

---

## 2. Functional Requirements (The "What")

### 2.1. Chat at Three Scope Levels

- **As a** user, **I want to** chat with Claude at different scope levels, **so that** I can get answers from the right context.
  - **Acceptance Criteria:**
    - [ ] **Library-wide chat:** Accessible from the main library page. Claude searches across all books (top 10-20 chunks) to answer questions.
    - [ ] **Group-level chat:** Accessible from within a selected group. Claude only searches books in that group.
    - [ ] **Book-level chat:** Accessible from the book detail page. Claude only searches within that specific book.
    - [ ] Each chat level is clearly labeled so the user knows the scope (e.g., "Chatting with: All Books" / "Chatting with: Spark group" / "Chatting with: High Performance Spark").

### 2.2. Conversational Chat UI

- **As a** user, **I want** a chat interface where I can have multi-turn conversations, **so that** I can ask follow-up questions naturally.
  - **Acceptance Criteria:**
    - [ ] The chat shows a message history with user messages and Claude's responses.
    - [ ] The user types a message and sends it (Enter key or send button).
    - [ ] Claude's response streams in real-time (not waiting for the full response).
    - [ ] Claude's responses include references to specific books, chapters, and pages when citing book content.
    - [ ] References are clickable — linking to the PDF/EPUB viewer at the right page.

### 2.3. RAG-Powered Responses

- **As a** user, **I want** Claude to use my book content when answering, **so that** responses are grounded in my actual library.
  - **Acceptance Criteria:**
    - [ ] Before answering, the system retrieves relevant chunks from the book library based on the user's question and the chat scope.
    - [ ] Retrieved chunks are passed to Claude as context along with the user's message.
    - [ ] If no relevant chunks are found, Claude answers from general knowledge and notes this.
    - [ ] The number of retrieved chunks is appropriate: ~10-20 for library-wide, ~10 for group, ~10 for book.

---

## 3. Scope and Boundaries

### In-Scope

- Chat UI component with message history and streaming responses.
- Three scope levels: library-wide, group, book.
- RAG retrieval scoped by level (all chunks, group chunks, book chunks).
- Clickable references to PDF/EPUB viewer.
- Backend chat endpoint using Claude API with streaming.

### Out-of-Scope

- Chat history persistence (conversations reset on page refresh).
- File uploads in chat.
- Multi-model support (Claude only).
- Chat in MCP (already handled by the MCP server).
