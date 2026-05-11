import { useState, type FormEvent } from "react";
import { SearchIcon, BookOpenIcon, ExternalLinkIcon, Loader2Icon } from "lucide-react";
import { useSearch, type SearchHit } from "@/api/search";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

function extractPath(viewerUrl: string): string {
  try {
    const url = new URL(viewerUrl);
    return url.pathname + url.search;
  } catch {
    return viewerUrl;
  }
}

function isEpubViewerUrl(url: string): boolean {
  return url.includes("/epub");
}

function SearchResultCard({ hit }: { hit: SearchHit }) {
  const path = extractPath(hit.viewer_url);
  const isEpub = isEpubViewerUrl(path);

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm transition-colors hover:bg-accent/30">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold">{hit.book_title}</h3>
          {hit.author && (
            <p className="text-sm text-muted-foreground">{hit.author}</p>
          )}
          <p className="mt-1 text-sm">
            <span className="font-medium">{hit.chapter_title}</span>
            <span className="text-muted-foreground"> &middot; Page {hit.page_number}</span>
          </p>
          <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
            {hit.snippet}
          </p>
        </div>
        <Link
          to={path}
          className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
        >
          <ExternalLinkIcon className="mr-1.5 h-3.5 w-3.5" />
          {isEpub ? "View in EPUB" : "View in PDF"}
        </Link>
      </div>
    </div>
  );
}

export function SearchPage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const { data, isLoading, isError } = useSearch(query);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed.length > 0) {
      setQuery(trimmed);
    }
  }

  const hasSearched = query.length > 0;
  const results = data?.results ?? [];

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight">Search Library</h1>
      </div>

      <form onSubmit={handleSubmit} className="mb-8 flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search by concept, pattern, or topic..."
            className="h-10 w-full rounded-md border bg-background pl-9 pr-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <Button type="submit" disabled={input.trim().length === 0}>
          Search
        </Button>
      </form>

      {!hasSearched && (
        <div className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
          <BookOpenIcon className="h-10 w-10" />
          <p className="text-sm">
            Search your book library by concept, pattern, or topic.
          </p>
        </div>
      )}

      {hasSearched && isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2Icon className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {hasSearched && isError && (
        <div className="py-16 text-center text-sm text-destructive">
          Something went wrong. Please try again.
        </div>
      )}

      {hasSearched && !isLoading && !isError && results.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
          <BookOpenIcon className="h-10 w-10" />
          <p className="text-sm">No matches found in your library.</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">{data?.message}</p>
          {results.map((hit) => (
            <SearchResultCard key={hit.chapter_id} hit={hit} />
          ))}
        </div>
      )}
    </div>
  );
}
