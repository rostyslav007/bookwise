import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post, put, del } from "@/api/client";

export interface Chapter {
  id: string;
  book_id: string;
  parent_id: string | null;
  title: string;
  level: number;
  order: number;
  start_page: number;
  end_page: number;
  created_at: string;
  children: Chapter[];
}

interface UpdateChapterPayload {
  chapterId: string;
  bookId: string;
  title?: string;
  start_page?: number;
  end_page?: number;
}

interface CreateChapterPayload {
  bookId: string;
  title: string;
  parent_id?: string;
  start_page: number;
  end_page: number;
}

interface MergeChaptersPayload {
  bookId: string;
  chapter_ids: [string, string];
}

const chaptersQueryKey = (bookId: string) => ["chapters", bookId] as const;

export function useChapters(bookId: string) {
  return useQuery<Chapter[]>({
    queryKey: chaptersQueryKey(bookId),
    queryFn: () => get<Chapter[]>(`/api/v1/books/${bookId}/chapters`),
    enabled: !!bookId,
  });
}

export function useUpdateChapter() {
  const queryClient = useQueryClient();

  return useMutation<Chapter, Error, UpdateChapterPayload>({
    mutationFn: ({ chapterId, title, start_page, end_page }) =>
      put<Chapter>(`/api/v1/chapters/${chapterId}`, {
        title,
        start_page,
        end_page,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: chaptersQueryKey(variables.bookId),
      });
    },
  });
}

export function useCreateChapter() {
  const queryClient = useQueryClient();

  return useMutation<Chapter, Error, CreateChapterPayload>({
    mutationFn: ({ bookId, title, parent_id, start_page, end_page }) =>
      post<Chapter>(`/api/v1/books/${bookId}/chapters`, {
        title,
        parent_id,
        start_page,
        end_page,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: chaptersQueryKey(variables.bookId),
      });
    },
  });
}

export function useDeleteChapter() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { chapterId: string; bookId: string }>({
    mutationFn: ({ chapterId }) => del(`/api/v1/chapters/${chapterId}`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: chaptersQueryKey(variables.bookId),
      });
    },
  });
}

export function useMergeChapters() {
  const queryClient = useQueryClient();

  return useMutation<Chapter, Error, MergeChaptersPayload>({
    mutationFn: ({ chapter_ids }) =>
      post<Chapter>("/api/v1/chapters/merge", { chapter_ids }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: chaptersQueryKey(variables.bookId),
      });
    },
  });
}

export type ChunkingStrategy = "headings" | "fixed";

interface ReindexPayload {
  bookId: string;
  strategy: ChunkingStrategy;
}

export function useReindexBook() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, ReindexPayload>({
    mutationFn: ({ bookId, strategy }) =>
      post<void>(`/api/v1/books/${bookId}/reindex?strategy=${strategy}`, {}),
    onSuccess: (_data, { bookId }) => {
      queryClient.invalidateQueries({
        queryKey: chaptersQueryKey(bookId),
      });
    },
  });
}
