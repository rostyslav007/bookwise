# Product Roadmap: BooksNavigationMCP

_This roadmap outlines the strategic direction for building a personal technical book navigation system. It focuses on the "what" and "why," not the technical "how."_

---

### Phase 1 — Foundation: Book Ingestion & Search

_The core pipeline: get books in, index them, and make them searchable._

- [x] **PDF Book Ingestion**
  - [x] **PDF Upload:** Allow uploading technical PDF books to the system.
  - [x] **Structure Extraction:** Automatically parse the table of contents, chapters, and page boundaries from uploaded PDFs.
  - [x] **Concept Indexing:** Index book content by concepts, patterns, and topics for fast retrieval.

- [x] **Book Catalog Management**
  - [x] **Add & Remove Books:** Manage the personal book library — add new books, remove old ones.
  - [x] **List Books:** View all indexed books with their metadata (title, author, chapter count).

---

### Phase 2 — Intelligence: MCP Server & Concept Search

_Make the indexed knowledge accessible to Claude during coding sessions._

- [x] **MCP Server for Claude**
  - [x] **Concept Search Tool:** Claude can query the index by concept/topic and get book + chapter + page references.
  - [x] **Chapter Content Retrieval:** Claude can retrieve relevant text chunks from matched chapters for inline context.
  - [x] **Books-First Fallback:** Search the personal library first; if not found, notify the user that the answer comes from general knowledge.

- [x] **In-Browser Book Viewing**
  - [x] **Open at Exact Page:** Launch the PDF in Chrome at the specific page where a concept is mentioned.
  - [x] **Highlight Relevant Chunks:** Highlight the matched text sections within the opened PDF.

---

### Phase 3 — Experience: Web UI

_A full browser-based interface for managing and exploring the book library._

- [x] **Book Management UI**
  - [x] **Upload Interface:** Drag-and-drop or file picker for uploading PDFs via the browser.
  - [x] **Library Browser:** Browse all indexed books, view metadata, and remove books.

- [x] **Search & Reading UI**
  - [x] **Concept Search:** Search across all books by concept, pattern, or topic from the browser.
  - [x] **Chapter Browser:** Browse chapters within a book, view content, and navigate between sections.
  - [x] **Integrated PDF Viewer:** Read books directly in the web UI with highlighting of relevant sections.
