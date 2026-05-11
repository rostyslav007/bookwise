import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { del, get, post, put } from "@/api/client";

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  scope: string;
  group_id: string | null;
  book_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

interface CreateSessionPayload {
  title: string;
  scope: string;
  group_id?: string | null;
  book_id?: string | null;
}

const SESSIONS_URL = "/api/v1/chat/sessions/";

function sessionsQueryKey(
  scope?: string,
  groupId?: string,
  bookId?: string,
) {
  return ["chat-sessions", scope, groupId, bookId] as const;
}

function sessionDetailQueryKey(sessionId: string) {
  return ["chat-session", sessionId] as const;
}

export function useChatSessions(
  scope?: string,
  groupId?: string,
  bookId?: string,
) {
  const params = new URLSearchParams();
  if (scope) params.set("scope", scope);
  if (groupId) params.set("group_id", groupId);
  if (bookId) params.set("book_id", bookId);
  const qs = params.toString();
  const url = qs ? `${SESSIONS_URL}?${qs}` : SESSIONS_URL;

  return useQuery<ChatSession[]>({
    queryKey: sessionsQueryKey(scope, groupId, bookId),
    queryFn: () => get<ChatSession[]>(url),
  });
}

export function useChatSessionDetail(sessionId: string | null) {
  return useQuery<ChatSessionDetail>({
    queryKey: sessionDetailQueryKey(sessionId ?? ""),
    queryFn: () => get<ChatSessionDetail>(`${SESSIONS_URL}${sessionId}`),
    enabled: !!sessionId,
  });
}

export function useCreateChatSession(
  scope?: string,
  groupId?: string,
  bookId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation<ChatSession, Error, CreateSessionPayload>({
    mutationFn: (payload) => post<ChatSession>(SESSIONS_URL, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sessionsQueryKey(scope, groupId, bookId),
      });
    },
  });
}

export function useDeleteChatSession(
  scope?: string,
  groupId?: string,
  bookId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => del(`${SESSIONS_URL}${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sessionsQueryKey(scope, groupId, bookId),
      });
    },
  });
}

export function useRenameChatSession(
  scope?: string,
  groupId?: string,
  bookId?: string,
) {
  const queryClient = useQueryClient();

  return useMutation<ChatSession, Error, { id: string; title: string }>({
    mutationFn: ({ id, title }) =>
      put<ChatSession>(`${SESSIONS_URL}${id}`, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sessionsQueryKey(scope, groupId, bookId),
      });
    },
  });
}

export async function streamChat(
  sessionId: string,
  message: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  signal: AbortSignal,
) {
  const response = await fetch("/api/v1/chat/stream/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const event of events) {
        for (const line of event.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6);
          if (raw === "[DONE]") {
            onDone();
            return;
          }
          try {
            const text = JSON.parse(raw) as string;
            onChunk(text);
          } catch {
            onChunk(raw);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  onDone();
}
