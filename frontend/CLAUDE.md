# Frontend

React 19 SPA with TypeScript, Vite, Tailwind CSS, shadcn/ui components.

## Structure

```
src/
  App.tsx              # Routes: /, /search, /books/:id, /books/:id/view, /books/:id/epub
  api/
    client.ts          # Fetch wrapper: get, post, put, patch, del + ApiError
    books.ts           # useBook, useBooks (auto-refetch if processing), useUploadBook, useUpdateBook, useDeleteBook
    groups.ts          # useGroups, useCreateGroup, useUpdateGroup, useDeleteGroup
    chapters.ts        # useChapters, useCreateChapter, useUpdateChapter, useDeleteChapter, useMergeChapters, useReindexBook (strategy param)
    search.ts          # useSearch(query) — enabled when query non-empty
  pages/
    LibraryPage.tsx    # Group icon grid (keyword→icon mapping) + sidebar + upload + book grid + ChatPanel
    BookDetailPage.tsx # Book metadata card (editable title) + chapter tree + reindex (strategy dropdown) + ChatPanel
    SearchPage.tsx     # Search input + ranked results with "View in PDF/EPUB" links
    PdfViewerPage.tsx  # react-pdf: page nav, zoom, customTextRenderer for highlight via ?highlight= param
    EpubViewerPage.tsx # epubjs: ArrayBuffer fetch, chapter sidebar TOC, font size, ?chapter= index param
  components/
    books/             # BookCard (status badge, click→detail), BookGrid, BookUploadZone (drag+drop, browse button), ProgressBar (SSE)
    chapters/          # ChapterList, ChapterItem (edit/delete/merge/view), AddChapterDialog
    groups/            # GroupSidebar (search link, groups list, create/rename/delete), GroupFormDialog
    chat/              # ChatPanel — fixed bottom panel, expandable, streaming SSE, markdown link parsing
    ui/                # shadcn: button, card, dialog, input, badge, dropdown-menu, alert-dialog, tooltip
  hooks/
    useSSE.ts          # EventSource hook: connect, receive messages, close on __DONE__
```

## Key Patterns

- **TanStack Query** for all server state — auto-cache, invalidation on mutations
- **URL trailing slash** convention: list endpoints end with `/`, ID endpoints don't
- **Lazy loading:** PdfViewerPage and EpubViewerPage loaded via React.lazy + Suspense
- **SSE streaming:** Chat uses fetch + ReadableStream (not EventSource) for POST support. Chunks are JSON-encoded.
- **Book references in chat:** Claude outputs `[label](viewer_url)` → frontend parses regex, renders as `<Link>` to viewer
- **Format-aware routing:** Book.format determines viewer route (/view for PDF, /epub for EPUB)
- **Auto-refetch:** useBooks polls every 3s when any book has status "processing"

## URL Params

- `/books/:id/view?page=5&highlight=Observer+pattern` — PDF viewer at page 5 with text highlighted
- `/books/:id/epub?chapter=3` — EPUB viewer at TOC entry index 3
- `/search?q=lazy+evaluation` — pre-filled search query

## Chat Panel (ChatPanel.tsx)

- Fixed bottom bar, click to expand (400px), scope label shows context
- Three scopes: library (all books), group (filtered), book (single)
- SSE format: `data: "json-encoded-text"\n\n` ... `data: [DONE]\n\n`
- Parses `[label](url)` in assistant messages as clickable router links

## Build & Test

```bash
npm run build      # Production build (Vite)
npm test           # Vitest component tests (14 tests)
npm run test:watch # Watch mode
```
