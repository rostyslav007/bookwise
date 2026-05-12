import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useBook, useDeleteBook, useUpdateBook } from "@/api/books";
import { useChapters, useReindexBook, type ChunkingStrategy } from "@/api/chapters";
import { ChapterList } from "@/components/chapters/ChapterList";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { ArrowLeft, Check, Download, Eye, Pencil, RefreshCw, Trash, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { useGroups } from "@/api/groups";

const STATUS_VARIANT: Record<string, string> = {
  processing:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  ready: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export function BookDetailPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const book = useBook(bookId!);
  const chapters = useChapters(bookId!);
  const reindex = useReindexBook();
  const updateBook = useUpdateBook();
  const { data: groups = [] } = useGroups();
  const deleteBook = useDeleteBook();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [chunkingStrategy, setChunkingStrategy] = useState<ChunkingStrategy>("headings");

  if (book.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading book...</p>
      </div>
    );
  }

  if (book.isError || !book.data) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4">
        <p className="text-destructive">
          {book.error?.message ?? "Book not found"}
        </p>
        <Link to="/" className="text-sm text-primary hover:underline">
          Back to library
        </Link>
      </div>
    );
  }

  const { data: bookData } = book;
  const groupName = groups.find((g) => g.id === bookData.group_id)?.name;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <Link
        to={bookData.group_id ? `/?group=${bookData.group_id}` : "/"}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        {groupName ? `Back to ${groupName} group` : "Back to library"}
      </Link>

      {/* Book metadata card */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
          <div className="space-y-1">
            {isEditingTitle ? (
              <div className="flex items-center gap-2">
                <Input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="h-8 text-xl font-semibold"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && editTitle.trim()) {
                      updateBook.mutate(
                        { id: bookId!, title: editTitle.trim() },
                        { onSuccess: () => setIsEditingTitle(false) },
                      );
                    }
                    if (e.key === "Escape") setIsEditingTitle(false);
                  }}
                />
                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => {
                    if (editTitle.trim()) {
                      updateBook.mutate(
                        { id: bookId!, title: editTitle.trim() },
                        { onSuccess: () => setIsEditingTitle(false) },
                      );
                    }
                  }}
                  disabled={!editTitle.trim() || updateBook.isPending}
                >
                  <Check className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => setIsEditingTitle(false)}
                >
                  <X className="size-4" />
                </Button>
              </div>
            ) : (
              <CardTitle
                className="group flex cursor-pointer items-center gap-2 text-xl"
                onClick={() => {
                  setEditTitle(bookData.title);
                  setIsEditingTitle(true);
                }}
              >
                {bookData.title}
                <Pencil className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100" />
              </CardTitle>
            )}
            {bookData.author && (
              <p className="text-sm text-muted-foreground">{bookData.author}</p>
            )}
          </div>
          <Badge
            variant="outline"
            className={STATUS_VARIANT[bookData.status] ?? ""}
          >
            {bookData.status}
          </Badge>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <div className="flex items-center justify-between">
            <div className="flex gap-4 text-sm text-muted-foreground">
              {bookData.page_count && <span>{bookData.page_count} pages</span>}
              <span>
                Created {new Date(bookData.created_at).toLocaleDateString()}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  navigate(
                    bookData.format === "epub"
                      ? `/books/${bookId}/epub`
                      : `/books/${bookId}/view`,
                  )
                }
              >
                <Eye className="size-3.5" />
                {bookData.format === "epub" ? "View EPUB" : "View PDF"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const a = document.createElement("a");
                  a.href = `/api/v1/books/${bookId}/${bookData.format === "epub" ? "file" : "pdf"}`;
                  a.download = `${bookData.title}.${bookData.format}`;
                  a.click();
                }}
              >
                <Download className="size-3.5" />
                Download
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={reindex.isPending}
                onClick={() => reindex.mutate({ bookId: bookId!, strategy: chunkingStrategy })}
              >
                <RefreshCw
                  className={`size-3.5 ${reindex.isPending ? "animate-spin" : ""}`}
                />
                {reindex.isPending ? "Re-indexing..." : "Re-index"}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteBook.isPending}
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash className="size-3.5" />
                Delete book
              </Button>
            </div>
          </div>
          <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground">
            <span>Indexing strategy:</span>
            <select
              value={chunkingStrategy}
              onChange={(e) => setChunkingStrategy(e.target.value as ChunkingStrategy)}
              disabled={reindex.isPending}
              className="rounded border bg-background px-2 py-1 text-xs"
            >
              <option value="headings">By headings</option>
              <option value="fixed">Fixed chunks (2000 chars)</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Chapter tree */}
      <Card>
        <CardContent className="pt-6">
          {chapters.isLoading && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Loading chapters...
            </p>
          )}
          {chapters.isError && (
            <p className="py-4 text-center text-sm text-destructive">
              Failed to load chapters: {chapters.error.message}
            </p>
          )}
          {chapters.data && (
            <ChapterList bookId={bookId!} bookFormat={bookData.format} chapters={chapters.data} />
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete book</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the book, its chapter structure,
              search index, and PDF file. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteBook.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={deleteBook.isPending}
              onClick={() =>
                deleteBook.mutate(bookId!, {
                  onSuccess: () => navigate("/"),
                })
              }
            >
              {deleteBook.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ChatPanel scope="book" scopeLabel={bookData.title} bookId={bookId} />
    </div>
  );
}
