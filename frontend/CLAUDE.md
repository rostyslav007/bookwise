# Frontend

React 19 SPA with TypeScript, Vite, Tailwind CSS, shadcn/ui components.

## Structure

```
src/
  App.tsx              # Routes: /, /search, /books/:bookId, /books/:bookId/view, /books/:bookId/epub
  api/
    client.ts          # Fetch wrapper: get, post, put, patch, del + ApiError
    books.ts           # useBook, useBooks (auto-refetch if processing), useUploadBook, useUpdateBook, useDeleteBook
    groups.ts          # useGroups, useCreateGroup, useUpdateGroup, useDeleteGroup
    chapters.ts        # useChapters, useCreateChapter, useUpdateChapter, useDeleteChapter, useMergeChapters, useReindexBook (strategy param)
    search.ts          # useSearch(query) — enabled when query non-empty
    chat.ts            # useChatSessions, useCreateChatSession, useDeleteChatSession, useRenameChatSession, useChatSessionDetail, streamChat (POST + ReadableStream SSE)
  pages/
    LibraryPage.tsx    # Group icon grid (keyword→icon mapping) + sidebar + upload + book grid + ChatPanel. Reads/writes ?group= URL param to preserve selected group
    BookDetailPage.tsx # Book metadata card (editable title) + chapter tree + reindex (strategy dropdown) + ChatPanel + Download button. "Back to {group} group" link with ?group= param. Uses useGroups for group name lookup
    SearchPage.tsx     # Search input + ranked results with "View in PDF/EPUB" links
    PdfViewerPage.tsx  # react-pdf: page nav, zoom, chapter sidebar (TocItem component with expand/collapse), keyword-based highlighting (stop-word filtered, not exact substring). PdfViewerPage.css for transparent mark text
    EpubViewerPage.tsx # epubjs: ArrayBuffer fetch, chapter sidebar TOC, font size. Accepts ?chapterId= (UUID) — fetches chapters from DB, matches title against epub.js TOC, falls back to spine index. Also supports legacy ?chapter=N
  components/
    layout/            # Header.tsx (Bookwise logo + Search nav link), Layout.tsx (wraps non-viewer routes with Header)
    books/             # BookCard (status badge, click→detail), BookGrid, BookUploadZone (drag+drop, browse button), ProgressBar (SSE)
    chapters/          # ChapterList, ChapterItem (edit/delete/merge/view — EPUB links use ?chapterId={uuid}, shows §N for EPUB instead of pp.N-N), AddChapterDialog
    groups/            # GroupSidebar (search link, groups list, create/rename/delete), GroupFormDialog
    chat/              # ChatPanel — fixed bottom panel, resizable via drag handle (pointer events), session sidebar, streaming SSE, react-markdown + @tailwindcss/typography for rendering
    ui/                # shadcn: button, card, dialog, input, badge, dropdown-menu, alert-dialog, tooltip
  hooks/
    useSSE.ts          # EventSource hook: connect, receive messages, close on __DONE__
```

## Key Patterns

- **TanStack Query** for all server state — auto-cache, invalidation on mutations
- **URL trailing slash** convention: list endpoints end with `/`, ID endpoints don't
- **Lazy loading:** PdfViewerPage and EpubViewerPage loaded via React.lazy + Suspense
- **Layout wrapper:** Non-viewer routes wrapped in `<Layout>` (Header + main). Viewer pages render full-screen without header
- **SSE streaming:** Chat uses fetch + ReadableStream (not EventSource) for POST support. Chunks are JSON-encoded.
- **Markdown chat rendering:** Assistant messages rendered with ReactMarkdown. Book reference links (`[label](viewer_url)`) detected via custom `a` component and rendered as styled `<Link>` with BookOpen icon (not regex-based parseBookReferences)
- **Resizable chat panel:** Drag handle uses pointer capture events to resize panel height (min 200px, max viewport minus header)
- **Format-aware routing:** Book.format determines viewer route (/view for PDF, /epub for EPUB)
- **Auto-refetch:** useBooks polls every 3s when any book has status "processing"
- **Keyword highlighting:** PdfViewerPage splits highlight text into words, filters stop words, highlights any text span containing a keyword (not exact substring match)

## URL Params

- `/books/:bookId/view?page=5&highlight=Observer+pattern` — PDF viewer at page 5 with keyword-based highlighting
- `/books/:bookId/epub?chapterId=<uuid>` — EPUB viewer navigated to chapter by DB UUID (title-matched against epub.js TOC)
- `/books/:bookId/epub?chapter=3` — Legacy: EPUB viewer at TOC entry index 3
- `/search?q=lazy+evaluation` — pre-filled search query
- `/?group=<uuid>` — Library page with group pre-selected

## Chat Panel (ChatPanel.tsx)

- Fixed bottom bar, click to expand, resizable via drag handle (pointer capture)
- Session sidebar: create, rename (double-click), delete sessions
- Three scopes: library (all books), group (filtered), book (single)
- SSE format: `data: "json-encoded-text"\n\n` ... `data: [DONE]\n\n`
- Tool-use based responses: user sees "Searching your books..." typing indicator, then streamed markdown answer
- Assistant messages rendered with react-markdown + prose styles (@tailwindcss/typography)
- Book reference links rendered via custom ReactMarkdown `a` component — detects `/books/*/view` or `/books/*/epub` URLs and renders as styled `<Link>` with BookOpen icon

## Dependencies (notable beyond React/Vite/Tailwind/shadcn)

- `react-markdown` — markdown rendering in chat messages
- `@tailwindcss/typography` — prose styles for chat markdown
- `react-pdf` — PDF viewer
- `epubjs` — EPUB viewer
- `@tanstack/react-query` — server state management

## Build & Test

```bash
npm run build      # Production build (Vite)
npm test           # Vitest component tests (14 tests)
npm run test:watch # Watch mode
```
