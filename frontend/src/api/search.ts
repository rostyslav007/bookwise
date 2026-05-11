import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";

interface SearchHit {
  book_title: string;
  author: string | null;
  chapter_title: string;
  chapter_id: string;
  page_number: number;
  snippet: string;
  relevance_score: number;
  source: string;
  viewer_url: string;
}

interface SearchResult {
  results: SearchHit[];
  source: string;
  message: string;
}

const SEARCH_QUERY_KEY = ["search"] as const;

export function useSearch(query: string) {
  return useQuery<SearchResult>({
    queryKey: [...SEARCH_QUERY_KEY, query],
    queryFn: () =>
      get<SearchResult>(`/api/v1/search/?q=${encodeURIComponent(query)}`),
    enabled: query.length > 0,
  });
}

export type { SearchHit, SearchResult };
