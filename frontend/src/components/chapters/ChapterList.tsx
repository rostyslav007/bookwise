import { useState } from "react";
import { ChapterItem } from "@/components/chapters/ChapterItem";
import { AddChapterDialog } from "@/components/chapters/AddChapterDialog";
import { useMergeChapters, type Chapter } from "@/api/chapters";
import { Button } from "@/components/ui/button";
import { Merge } from "lucide-react";

interface ChapterListProps {
  bookId: string;
  bookFormat: "pdf" | "epub";
  chapters: Chapter[];
}

export function ChapterList({ bookId, bookFormat, chapters }: ChapterListProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const mergeChapters = useMergeChapters();

  function toggleSelection(chapterId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(chapterId)) {
        next.delete(chapterId);
      } else {
        next.add(chapterId);
      }
      return next;
    });
  }

  function areMergeableSelection(): boolean {
    if (selectedIds.size !== 2) return false;
    const ids = Array.from(selectedIds);
    return areSiblingsAdjacent(chapters, ids[0], ids[1]);
  }

  function handleMerge() {
    const ids = Array.from(selectedIds) as [string, string];
    mergeChapters.mutate(
      { bookId, chapter_ids: ids },
      { onSuccess: () => setSelectedIds(new Set()) }
    );
  }

  if (chapters.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 py-8 text-muted-foreground">
        <p>No chapters found.</p>
        <AddChapterDialog bookId={bookId} />
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between pb-2">
        <h3 className="text-sm font-medium text-muted-foreground">Chapters</h3>
        <div className="flex gap-2">
          {selectedIds.size === 2 && (
            <Button
              variant="outline"
              size="sm"
              disabled={!areMergeableSelection() || mergeChapters.isPending}
              onClick={handleMerge}
            >
              <Merge className="size-3.5" />
              {mergeChapters.isPending ? "Merging..." : "Merge selected"}
            </Button>
          )}
          <AddChapterDialog bookId={bookId} />
        </div>
      </div>
      {chapters.map((chapter) => (
        <ChapterItem
          key={chapter.id}
          bookId={bookId}
          bookFormat={bookFormat}
          chapter={chapter}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelection}
        />
      ))}
    </div>
  );
}

function areSiblingsAdjacent(
  chapters: Chapter[],
  idA: string,
  idB: string
): boolean {
  const indexA = chapters.findIndex((c) => c.id === idA);
  const indexB = chapters.findIndex((c) => c.id === idB);
  if (indexA !== -1 && indexB !== -1) {
    return Math.abs(indexA - indexB) === 1;
  }
  return chapters.some((c) => areSiblingsAdjacent(c.children, idA, idB));
}
