import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, patch, del, ApiError } from "@/api/client";

export interface Book {
  id: string;
  group_id: string;
  title: string;
  author: string | null;
  file_path: string;
  page_count: number | null;
  status: "processing" | "ready" | "error";
  created_at: string;
  updated_at: string;
  format: "pdf" | "epub";
}

interface UploadBookPayload {
  file: File;
  groupId: string;
}

const BOOKS_QUERY_KEY = ["books"] as const;
const BOOKS_URL = "/api/v1/books/";

export function useBook(bookId: string) {
  return useQuery<Book>({
    queryKey: [...BOOKS_QUERY_KEY, bookId],
    queryFn: () => get<Book>(`/api/v1/books/${bookId}`),
    enabled: !!bookId,
  });
}

export function useBooks(groupId?: string) {
  return useQuery<Book[]>({
    queryKey: [...BOOKS_QUERY_KEY, groupId],
    queryFn: () => {
      const url = groupId ? `${BOOKS_URL}?group_id=${groupId}` : BOOKS_URL;
      return get<Book[]>(url);
    },
    refetchInterval: (query) => {
      const books = query.state.data;
      if (books?.some((b) => b.status === "processing")) return 3000;
      return false;
    },
  });
}

export function useUpdateBook() {
  const queryClient = useQueryClient();
  return useMutation<Book, Error, { id: string; title: string }>({
    mutationFn: ({ id, title }) => patch<Book>(`/api/v1/books/${id}`, { title }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: [...BOOKS_QUERY_KEY, id] });
      queryClient.invalidateQueries({ queryKey: BOOKS_QUERY_KEY });
    },
  });
}

export function useDeleteBook() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => del(`/api/v1/books/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BOOKS_QUERY_KEY });
    },
  });
}

export function useUploadBook() {
  const queryClient = useQueryClient();

  return useMutation<Book, Error, UploadBookPayload>({
    mutationFn: async ({ file, groupId }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("group_id", groupId);

      const response = await fetch(BOOKS_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const body = await response.text().catch(() => null);
        throw new ApiError(response.status, response.statusText, body);
      }

      return response.json() as Promise<Book>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BOOKS_QUERY_KEY });
    },
  });
}
