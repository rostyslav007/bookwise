# Backend

FastAPI async application serving REST API, MCP server, and book processing pipeline.

## Structure

```
app/
  main.py              # FastAPI app, 5 routers: groups, books, chapters, search, chat
  config.py            # pydantic-settings from .env
  database.py          # async SQLAlchemy engine + session factory + Base
  mcp_server.py        # MCP stdio server: search_books + get_chapter_content tools
  models/              # SQLAlchemy ORM: Group, Book (format+status enums), Chapter (self-ref hierarchy), ChunkEmbedding (pgvector 384-dim)
  schemas/             # Pydantic: GroupCreate/Response, BookUpdate/Response, ChapterCreate/Update/Merge/Response (recursive)
  routers/
    groups.py          # CRUD /api/v1/groups/
    books.py           # Upload, list, PATCH title, DELETE, serve PDF/EPUB, SSE progress, chapters tree, reindex (strategy param)
    chapters.py        # CRUD + merge /api/v1/chapters/
    search.py          # GET /api/v1/search/?q=...&group_id=...&book_id=...
    chat.py            # POST /api/v1/chat/ — SSE streaming RAG chat
  services/
    book_service.py         # CRUD, upload_and_create (validates MIME: pdf/epub)
    group_service.py        # CRUD, cascade delete (removes PDF files)
    chapter_service.py      # CRUD + merge (re-parents children)
    processing_service.py   # CORE: process_book() pipeline — PDF/EPUB branching, metadata, TOC, chunking, embedding
    embedding_service.py    # Lazy-loaded SentenceTransformer, encode(texts) → vectors
    search_service.py       # pgvector cosine similarity, scoped by group/book, builds viewer_url
    chat_service.py         # RAG retrieval + Claude Bedrock/API streaming
    claude_service.py       # AI structure generation (hierarchical TOC from page samples)
    epub_parser_service.py  # ebooklib: metadata, TOC, chapter text+HTML extraction
    progress_tracker.py     # In-memory singleton, asyncio.Queue fan-out for SSE
alembic/               # 6 migrations: groups → books → chapters → chunks → cascade FK → format column
tests/                 # pytest-asyncio, uses books_test DB, 54+ tests
```

## Processing Pipeline (processing_service.py)

```
process_book(book_id)
├── PDF: _process_pdf(book)
│   ├── _extract_metadata(book, doc)         # PyMuPDF: title, author, page_count
│   ├── _extract_page_samples(doc)           # First 50 pages, 2000 chars each
│   ├── _generate_structure(...)             # Claude AI → hierarchical JSON (fallback: raw TOC)
│   ├── _save_chapters(book_id, structure)   # Recursive insert with parent_id
│   └── _embed_chapters(book_id, file, strategy)  # Heading-based or fixed chunking
└── EPUB: _process_epub(book)
    ├── EpubParserService.extract_metadata() 
    ├── EpubParserService.extract_toc_and_texts()  # Returns title, text, html, href per spine item
    ├── _save_chapters(book_id, structure)
    └── _embed_epub_chapters(book_id, chapters, strategy)  # HTML h1/h2/h3 splitting or fixed
```

## Chunking Strategies (ChunkingStrategy enum)

- **HEADINGS (default):** PDF = font-size > 115% of median → heading boundary. EPUB = split on h1/h2/h3 tags. Sections >4000 chars sub-split with overlap.
- **FIXED:** 2000-char sliding window with 400-char overlap.
- Configurable per-reindex via `POST /books/{id}/reindex?strategy=headings|fixed`

## Chat (chat_service.py)

- Retrieves 10-15 chunks scoped by group/book
- System prompt includes excerpts with viewer_url — Claude outputs `[label](viewer_url)` markdown links
- Client: `AsyncAnthropicBedrock` if `AWS_BEARER_TOKEN_BEDROCK` set, else `AsyncAnthropic`
- SSE: JSON-encoded chunks → `data: "text"\n\n` → sentinel `data: [DONE]\n\n`

## Key Dependencies

fastapi, sqlalchemy[asyncio], asyncpg, pymupdf, ebooklib, beautifulsoup4,
sentence-transformers, pgvector, anthropic[bedrock], mcp[cli], pydantic-settings
