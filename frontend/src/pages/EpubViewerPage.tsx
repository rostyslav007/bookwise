import { useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import ePub from 'epubjs';
import type { NavItem } from 'epubjs';
import type Rendition from 'epubjs/types/rendition';
import type Navigation from 'epubjs/types/navigation';
import { ArrowLeft, ChevronLeft, ChevronRight, Minus, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useChapters } from '@/api/chapters';

const MIN_FONT_SIZE = 60;
const MAX_FONT_SIZE = 200;
const FONT_SIZE_STEP = 10;

interface FlatChapter { id: string; title: string; order: number; start_page: number }

function flattenChapters(chapters: { id: string; title: string; order: number; start_page: number; children: any[] }[]): FlatChapter[] {
  const result: FlatChapter[] = [];
  for (const ch of chapters) {
    result.push({ id: ch.id, title: ch.title, order: ch.order, start_page: ch.start_page });
    if (ch.children?.length) result.push(...flattenChapters(ch.children));
  }
  return result;
}

export default function EpubViewerPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const [searchParams] = useSearchParams();
  const targetChapterId = searchParams.get('chapterId');
  const legacyChapterIndex = searchParams.get('chapter');
  const { data: chapters } = useChapters(bookId!);

  const viewerRef = useRef<HTMLDivElement>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const [toc, setToc] = useState<NavItem[]>([]);
  const [fontSize, setFontSize] = useState(100);

  useEffect(() => {
    if (!viewerRef.current || !bookId) return;

    let destroyed = false;

    async function loadEpub() {
      // Fetch EPUB as ArrayBuffer — epub.js works more reliably with binary data
      const response = await fetch(`/api/v1/books/${bookId}/file`);
      if (!response.ok || destroyed) return;
      const arrayBuffer = await response.arrayBuffer();
      if (destroyed || !viewerRef.current) return;

      const container = viewerRef.current;
      const rect = container.getBoundingClientRect();

      const book = ePub(arrayBuffer);
      const rendition = book.renderTo(container, {
        width: rect.width,
        height: rect.height,
        spread: 'none',
      });

      renditionRef.current = rendition;

      book.loaded.navigation.then((nav: Navigation) => {
        if (!destroyed) setToc(nav.toc);

        // Flatten TOC for searching (includes nested items)
        const allTocItems: NavItem[] = [];
        function walkToc(items: NavItem[]) {
          for (const item of items) {
            allTocItems.push(item);
            if (item.subitems?.length) walkToc(item.subitems);
          }
        }
        walkToc(nav.toc);

        // Navigate to target chapter
        if (targetChapterId && chapters) {
          // Find chapter title from DB, then match in TOC by title
          const flat = flattenChapters(chapters);
          const dbChapter = flat.find((ch) => ch.id === targetChapterId);
          if (dbChapter) {
            const tocMatch = allTocItems.find((t) =>
              t.label.trim().toLowerCase() === dbChapter.title.trim().toLowerCase()
            );
            if (tocMatch) {
              rendition.display(tocMatch.href);
            } else {
              // Fallback: navigate by spine index (start_page is 1-indexed spine position)
              const spineItem = book.spine.get(dbChapter.start_page - 1);
              if (spineItem) {
                rendition.display(spineItem.href);
              } else {
                rendition.display();
              }
            }
          } else {
            rendition.display();
          }
        } else if (legacyChapterIndex && nav.toc.length > 0) {
          // Backwards compatible: support ?chapter=N
          const index = Number(legacyChapterIndex);
          if (!Number.isNaN(index) && index < nav.toc.length) {
            rendition.display(nav.toc[index].href);
          } else {
            rendition.display();
          }
        } else {
          rendition.display();
        }
      });

      return () => {
        destroyed = true;
        rendition.destroy();
        book.destroy();
      };
    }

    const cleanupPromise = loadEpub();
    return () => {
      destroyed = true;
      cleanupPromise.then((cleanup) => cleanup?.());
    };
  }, [bookId, targetChapterId, legacyChapterIndex, chapters]);

  useEffect(() => {
    renditionRef.current?.themes.fontSize(`${fontSize}%`);
  }, [fontSize]);

  function goNext() {
    renditionRef.current?.next();
  }

  function goPrev() {
    renditionRef.current?.prev();
  }

  function navigateTo(href: string) {
    renditionRef.current?.display(href);
  }

  function decreaseFontSize() {
    setFontSize((s) => Math.max(MIN_FONT_SIZE, s - FONT_SIZE_STEP));
  }

  function increaseFontSize() {
    setFontSize((s) => Math.min(MAX_FONT_SIZE, s + FONT_SIZE_STEP));
  }

  return (
    <div className="flex h-screen flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b px-4 py-2">
        <Link
          to={`/books/${bookId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Back to book
        </Link>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={goPrev}>
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={goNext}>
            <ChevronRight className="size-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={decreaseFontSize}>
            <Minus className="size-4" />
          </Button>
          <span className="text-sm">{fontSize}%</span>
          <Button variant="outline" size="sm" onClick={increaseFontSize}>
            <Plus className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* TOC sidebar */}
        <nav className="w-64 shrink-0 overflow-y-auto border-r bg-gray-50 p-4">
          <h3 className="mb-2 text-sm font-semibold">Chapters</h3>
          <ul className="space-y-1">
            {toc.map((item) => (
              <li key={item.id}>
                <button
                  className="w-full truncate text-left text-sm text-muted-foreground hover:text-foreground"
                  onClick={() => navigateTo(item.href)}
                >
                  {item.label}
                </button>
                {item.subitems && item.subitems.length > 0 && (
                  <ul className="ml-3 space-y-0.5">
                    {item.subitems.map((sub) => (
                      <li key={sub.id}>
                        <button
                          className="w-full truncate text-left text-xs text-muted-foreground hover:text-foreground"
                          onClick={() => navigateTo(sub.href)}
                        >
                          {sub.label}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </nav>

        {/* EPUB content */}
        <div ref={viewerRef} className="flex-1 overflow-hidden" />
      </div>
    </div>
  );
}
