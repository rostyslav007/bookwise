import { useBooks } from "@/api/books";
import { BookCard } from "@/components/books/BookCard";

interface BookGridProps {
  groupId: string;
}

export function BookGrid({ groupId }: BookGridProps) {
  const { data: books, isLoading, isError } = useBooks(groupId);

  if (isLoading) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        Loading books...
      </p>
    );
  }

  if (isError) {
    return (
      <p className="py-8 text-center text-sm text-destructive">
        Failed to load books.
      </p>
    );
  }

  if (!books || books.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No books in this group
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {books.map((book) => (
        <BookCard key={book.id} book={book} />
      ))}
    </div>
  );
}
