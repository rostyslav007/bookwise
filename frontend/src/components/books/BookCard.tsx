import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/books/ProgressBar";
import { useSSE } from "@/hooks/useSSE";
import type { Book } from "@/api/books";

interface BookCardProps {
  book: Book;
}

const STATUS_VARIANT: Record<Book["status"], string> = {
  processing:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  ready: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export function BookCard({ book }: BookCardProps) {
  const navigate = useNavigate();
  const isProcessing = book.status === "processing";
  const isReady = book.status === "ready";
  const sseUrl = isProcessing ? `/api/v1/books/${book.id}/progress` : null;
  const progressStep = useSSE(sseUrl);

  function handleClick() {
    if (isReady) {
      navigate(`/books/${book.id}`);
    }
  }

  return (
    <Card
      className={isReady ? "cursor-pointer transition-shadow hover:shadow-md" : ""}
      onClick={handleClick}
    >
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
        <CardTitle className="text-base leading-snug">{book.title}</CardTitle>
        <Badge
          variant="outline"
          className={`${STATUS_VARIANT[book.status]}${isProcessing ? " animate-pulse" : ""}`}
        >
          {book.status}
        </Badge>
      </CardHeader>
      <CardContent className="pt-0">
        {book.author && (
          <p className="text-sm text-muted-foreground">{book.author}</p>
        )}
        {book.page_count && (
          <p className="text-sm text-muted-foreground">
            {book.page_count} pages
          </p>
        )}
        {isProcessing && progressStep && <ProgressBar step={progressStep} />}
      </CardContent>
    </Card>
  );
}
