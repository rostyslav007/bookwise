# Backend

FastAPI async application serving REST API, MCP server, and book processing pipeline.

## Structure

```
app/
  main.py              # FastAPI app "Bookwise", 5 routers: groups, books, chapters, search, chat
                       # Startup lifespan resets stuck "processing" books to "ready"
  config.py            # pydantic-settings from .env
  database.py          # Two async SQLAlchemy pools:
                       #   main (pool_size=8, max_overflow=4) — UI/API queries
                       #   background (pool_size=4, max_overflow=2) — indexing/processing
  mcp_server.py        # "Bookwise" MCP stdio server: search_books, get_chapter_content, explain_from_book
  models/              # SQLAlchemy ORM: Group, Book (format+status enums), Chapter (self-ref hierarchy),
                       #   ChunkEmbedding (pgvector 384-dim), ChatSession, ChatMessage
  schemas/             # Pydantic: GroupCreate/Response, BookUpdate/Response, ChapterCreate/Update/Merge/Response (recursive), ChatSession/Message
  routers/
    groups.py          # CRUD /api/v1/groups/
    books.py           # Upload, list, PATCH title, DELETE, serve PDF/EPUB, SSE progress, chapters tree, reindex (strategy param)
    chapters.py        # CRUD + merge /api/v1/chapters/
    search.py          # GET /api/v1/search/?q=...&group_id=...&book_id=...
    chat.py            # POST /api/v1/chat/ — SSE streaming tool-use chat
  services/
    book_service.py         # CRUD, upload_and_create (validates MIME: pdf/epub)
    group_service.py        # CRUD, cascade delete (removes PDF files)
    chapter_service.py      # CRUD + merge (re-parents children)
    processing_service.py   # CORE: process_book() pipeline — PDF/EPUB branching, metadata, TOC, chunking, embedding
    embedding_service.py    # Lazy-loaded SentenceTransformer, encode() (sync) + encode_async() (thread pool via run_in_executor)
    search_service.py       # pgvector cosine similarity, fuzzy_match_book, search_by_page_range, explain_from_book, extract_page_images, _resolve_book_path helper
    chat_service.py         # Tool-use Claude chat: 3-step flow (tool selection → execution → streaming answer)
    chat_session_service.py # CRUD for ChatSession/ChatMessage persistence
    claude_service.py       # AI structure generation (hierarchical TOC from page samples)
    epub_parser_service.py  # ebooklib: metadata, recursive TOC traversal (_build_toc_map walks nested entries), _extract_title_from_html fallback
    progress_tracker.py     # In-memory singleton, asyncio.Queue fan-out for SSE
alembic/               # 8 migrations: groups → books → chapters → chunks → cascade FK → format column → chat_sessions → file_hash
tests/                 # pytest-asyncio, uses books_test DB, 54+ tests
```

## Processing Pipeline (processing_service.py)

```
process_book(book_id)
├── PDF: _process_pdf(book)
│   ├── _extract_metadata(book, doc)         # PyMuPDF: title, author, page_count
│   ├── _extract_page_samples(doc)           # First 50 pages, 2000 chars each
│   ├── _generate_structure(...)             # Claude AI → hierarchical JSON (fallback: _toc_to_structure from raw PyMuPDF TOC)
│   │   └── _toc_to_structure(toc, total_pages)  # Hierarchical tree from PyMuPDF [level, title, page] entries using a stack
│   ├── _save_chapters(book_id, structure)   # Recursive insert with parent_id
│   └── _embed_chapters(book_id, file, strategy)  # TOC-based or heading-based or fixed chunking, batched (64)
└── EPUB: _process_epub(book)
    ├── EpubParserService.extract_metadata() 
    ├── EpubParserService.extract_toc_and_texts()  # Recursive _build_toc_map, _extract_title_from_html fallback
    ├── _save_chapters(book_id, structure)
    └── _embed_epub_chapters(book_id, chapters, strategy)  # HTML h1/h2/h3 splitting or fixed, batched (64)
```

## Chunking Strategies (ChunkingStrategy enum)

- **TOC-based (primary for PDF):** Leaf chapters from the TOC become chunks. Sections >4000 chars sub-split with overlap. Sections <200 chars (_MIN_CHUNK_SIZE) merged with the next sibling.
- **HEADINGS (fallback, no TOC only):** PDF = font-size > 115% of median → heading boundary. EPUB = split on h1/h2/h3 tags. Sections >4000 chars sub-split with overlap.
- **FIXED:** 2000-char sliding window with 400-char overlap.
- Configurable per-reindex via `POST /books/{id}/reindex?strategy=headings|fixed`
- Embedding batched in groups of 64 for memory efficiency.

## Chat (chat_service.py)

- **Tool-use based** — NOT pre-fetched RAG context injection
- Tools defined as Claude tool_use schemas: `search_books`, `explain_from_book`
- **3-step flow:**
  1. Non-streaming round: Claude decides which tools to call
  2. Tool execution: creates own DB sessions via `async_session_factory()`, runs SearchService methods
  3. Streaming answer: tool results injected into system prompt, page images added as multimodal content blocks
- System prompt enforces conversational prose style (no bullet lists, no headers, natural citations)
- Client: `AsyncAnthropicBedrock` if `AWS_BEARER_TOKEN_BEDROCK` set, else `AsyncAnthropic`
- SSE: JSON-encoded chunks → `data: "text"\n\n` → sentinel `data: [DONE]\n\n`

## Key Dependencies

fastapi, sqlalchemy[asyncio], asyncpg, pymupdf, ebooklib, beautifulsoup4,
sentence-transformers, pgvector, anthropic[bedrock], mcp[cli], pydantic-settings
