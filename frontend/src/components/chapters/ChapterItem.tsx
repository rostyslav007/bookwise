import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useUpdateChapter,
  useDeleteChapter,
  type Chapter,
} from "@/api/chapters";
import { AddChapterDialog } from "@/components/chapters/AddChapterDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Pencil,
  Trash2,
} from "lucide-react";

interface ChapterItemProps {
  bookId: string;
  bookFormat: "pdf" | "epub";
  chapter: Chapter;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
}

export function ChapterItem({
  bookId,
  bookFormat,
  chapter,
  selectedIds,
  onToggleSelect,
}: ChapterItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(chapter.title);
  const [editStartPage, setEditStartPage] = useState(chapter.start_page);
  const [editEndPage, setEditEndPage] = useState(chapter.end_page);
  const [isExpanded, setIsExpanded] = useState(true);

  const navigate = useNavigate();
  const updateChapter = useUpdateChapter();
  const deleteChapter = useDeleteChapter();

  const hasChildren = chapter.children.length > 0;
  const isSelected = selectedIds.has(chapter.id);

  function startEditing() {
    setEditTitle(chapter.title);
    setEditStartPage(chapter.start_page);
    setEditEndPage(chapter.end_page);
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
  }

  function saveEdit() {
    updateChapter.mutate(
      {
        chapterId: chapter.id,
        bookId,
        title: editTitle,
        start_page: editStartPage,
        end_page: editEndPage,
      },
      { onSuccess: () => setIsEditing(false) }
    );
  }

  function handleDelete() {
    deleteChapter.mutate({ chapterId: chapter.id, bookId });
  }

  return (
    <div>
      <div
        className={`flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50 ${
          isSelected ? "bg-primary/10 ring-1 ring-primary/30" : ""
        }`}
        style={{ paddingLeft: `${chapter.level * 24 + 8}px` }}
      >
        {/* Expand/collapse toggle */}
        {hasChildren ? (
          <button
            className="shrink-0 text-muted-foreground hover:text-foreground"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <ChevronDown className="size-4" />
            ) : (
              <ChevronRight className="size-4" />
            )}
          </button>
        ) : (
          <span className="w-4 shrink-0" />
        )}

        {/* Selection checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelect(chapter.id)}
          className="shrink-0 accent-primary"
        />

        {isEditing ? (
          <div className="flex flex-1 items-center gap-2">
            <Input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="h-7 flex-1"
              autoFocus
            />
            <Input
              type="number"
              value={editStartPage}
              onChange={(e) => setEditStartPage(Number(e.target.value))}
              className="h-7 w-20"
              min={1}
              placeholder="Start"
            />
            <Input
              type="number"
              value={editEndPage}
              onChange={(e) => setEditEndPage(Number(e.target.value))}
              className="h-7 w-20"
              min={1}
              placeholder="End"
            />
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={saveEdit}
              disabled={updateChapter.isPending}
            >
              <Check className="size-3.5" />
            </Button>
            <Button variant="ghost" size="icon-xs" onClick={cancelEditing}>
              <X className="size-3.5" />
            </Button>
          </div>
        ) : (
          <>
            <span className="flex-1 truncate text-sm">{chapter.title}</span>
            <span className="shrink-0 text-xs text-muted-foreground">
              {bookFormat === "epub"
                ? `§${chapter.start_page}`
                : `pp. ${chapter.start_page}-${chapter.end_page}`}
            </span>
            <div className="flex shrink-0 gap-0.5">
              <Button
                variant="ghost"
                size="icon-xs"
                title={bookFormat === "epub" ? "View in EPUB" : "View in PDF"}
                onClick={() =>
                  navigate(
                    bookFormat === "epub"
                      ? `/books/${bookId}/epub?chapterId=${chapter.id}`
                      : `/books/${bookId}/view?page=${chapter.start_page}`,
                  )
                }
              >
                <BookOpen className="size-3" />
              </Button>
              <Button variant="ghost" size="icon-xs" onClick={startEditing}>
                <Pencil className="size-3" />
              </Button>
              <AddChapterDialog
                bookId={bookId}
                parentId={chapter.id}
                triggerSize="icon-xs"
              />
              <AlertDialog>
                <AlertDialogTrigger
                  render={
                    <Button variant="ghost" size="icon-xs">
                      <Trash2 className="size-3 text-destructive" />
                    </Button>
                  }
                />
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete chapter</AlertDialogTitle>
                    <AlertDialogDescription>
                      Are you sure you want to delete &quot;{chapter.title}
                      &quot;? This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      variant="destructive"
                      onClick={handleDelete}
                    >
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </>
        )}
      </div>

      {/* Recursive children */}
      {hasChildren && isExpanded && (
        <div>
          {chapter.children.map((child) => (
            <ChapterItem
              key={child.id}
              bookId={bookId}
              bookFormat={bookFormat}
              chapter={child}
              selectedIds={selectedIds}
              onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
