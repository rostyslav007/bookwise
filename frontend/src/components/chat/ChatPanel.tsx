import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Plus,
  Send,
  Trash2,
} from "lucide-react";
import {
  type ChatSession,
  streamChat,
  useChatSessions,
  useCreateChatSession,
  useDeleteChatSession,
  useRenameChatSession,
  useChatSessionDetail,
} from "@/api/chat";

type ChatScope = "library" | "group" | "book";

interface ChatPanelProps {
  scope: ChatScope;
  scopeLabel: string;
  groupId?: string;
  bookId?: string;
}

interface LocalMessage {
  role: "user" | "assistant";
  content: string;
}

function extractPath(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.pathname + parsed.search;
  } catch {
    return url;
  }
}

function isBookReferenceLink(href: string): boolean {
  return href.includes("/books/") && (href.includes("/view") || href.includes("/epub"));
}

function MessageBubble({ message }: { message: LocalMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-primary text-primary-foreground whitespace-pre-wrap"
            : "bg-muted text-foreground prose prose-sm prose-neutral max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
        }`}
      >
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            components={{
              a: ({ href, children }) => {
                const url = href ?? "";
                const path = extractPath(url);
                if (isBookReferenceLink(url) || isBookReferenceLink(path)) {
                  return (
                    <Link
                      to={path}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mx-0.5 inline-flex items-center gap-1 rounded-md bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 no-underline"
                    >
                      <BookOpen className="size-3" />
                      {children}
                    </Link>
                  );
                }
                return (
                  <a href={url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    {children}
                  </a>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-1 rounded-lg bg-muted px-3 py-2">
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function SessionListItem({
  session,
  isActive,
  onSelect,
  onDelete,
  onRename,
}: {
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(session.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const commitRename = () => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== session.title) {
      onRename(trimmed);
    }
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1">
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") {
              setEditValue(session.title);
              setIsEditing(false);
            }
          }}
          className="min-w-0 flex-1 rounded border bg-background px-1 py-0.5 text-xs outline-none ring-ring focus:ring-1"
        />
      </div>
    );
  }

  return (
    <div
      className={`group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
        isActive
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted"
      }`}
      onClick={onSelect}
      onDoubleClick={(e) => {
        e.stopPropagation();
        setEditValue(session.title);
        setIsEditing(true);
      }}
    >
      <MessageSquare className="size-3 shrink-0" />
      <span className="flex-1 truncate">{session.title}</span>
      <button
        type="button"
        className="shrink-0 rounded p-0.5 opacity-0 hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        title="Delete session"
      >
        <Trash2 className="size-3" />
      </button>
    </div>
  );
}

export function ChatPanel({ scope, scopeLabel, groupId, bookId }: ChatPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [panelHeight, setPanelHeight] = useState(400);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const isDraggingRef = useRef(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);

  const handleResizePointerDown = useCallback((e: ReactPointerEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;
    startYRef.current = e.clientY;
    startHeightRef.current = panelHeight;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [panelHeight]);

  const handleResizePointerMove = useCallback((e: ReactPointerEvent) => {
    if (!isDraggingRef.current) return;
    const delta = startYRef.current - e.clientY;
    const headerHeight = 56;
    const chatBarHeight = 40;
    const maxHeight = window.innerHeight - headerHeight - chatBarHeight;
    setPanelHeight(Math.min(maxHeight, Math.max(200, startHeightRef.current + delta)));
  }, []);

  const handleResizePointerUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);
  const queryClient = useQueryClient();

  const { data: sessions = [] } = useChatSessions(scope, groupId, bookId);
  const { data: sessionDetail } = useChatSessionDetail(activeSessionId);
  const createSession = useCreateChatSession(scope, groupId, bookId);
  const deleteSession = useDeleteChatSession(scope, groupId, bookId);
  const renameSession = useRenameChatSession(scope, groupId, bookId);

  // Sync messages from loaded session detail
  useEffect(() => {
    if (sessionDetail && !isStreaming) {
      setMessages(
        sessionDetail.messages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
      );
    }
  }, [sessionDetail, isStreaming]);

  // Reset active session when scope changes
  useEffect(() => {
    setActiveSessionId(null);
    setMessages([]);
  }, [scope, groupId, bookId]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming, scrollToBottom]);

  const handleNewSession = useCallback(async () => {
    const title = `Chat ${new Date().toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`;
    const session = await createSession.mutateAsync({
      title,
      scope,
      group_id: groupId ?? null,
      book_id: bookId ?? null,
    });
    setActiveSessionId(session.id);
    setMessages([]);
  }, [createSession, scope, groupId, bookId]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    // Auto-create session if none active
    let sessionId = activeSessionId;
    if (!sessionId) {
      const title = trimmed.length > 40 ? trimmed.slice(0, 40) + "..." : trimmed;
      const session = await createSession.mutateAsync({
        title,
        scope,
        group_id: groupId ?? null,
        book_id: bookId ?? null,
      });
      sessionId = session.id;
      setActiveSessionId(sessionId);
    }

    const userMessage: LocalMessage = { role: "user", content: trimmed };
    const updatedMessages = [...messages, userMessage];

    setMessages(updatedMessages);
    setInput("");
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    let assistantContent = "";

    try {
      await streamChat(
        sessionId,
        trimmed,
        (chunk) => {
          assistantContent += chunk;
          const snapshot = assistantContent;
          setMessages([
            ...updatedMessages,
            { role: "assistant", content: snapshot },
          ]);
        },
        () => {
          /* done handled after await */
        },
        controller.signal,
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const errorText =
        assistantContent || "Sorry, something went wrong. Please try again.";
      setMessages([
        ...updatedMessages,
        { role: "assistant", content: errorText },
      ]);
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
      // Refresh session list (updated_at changed) and session detail
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      if (sessionId) {
        queryClient.invalidateQueries({
          queryKey: ["chat-session", sessionId],
        });
      }
    }
  }, [
    input,
    isStreaming,
    messages,
    activeSessionId,
    createSession,
    scope,
    groupId,
    bookId,
    queryClient,
  ]);

  const handleDeleteSession = useCallback(
    async (id: string) => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      await deleteSession.mutateAsync(id);
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
        setIsStreaming(false);
      }
    },
    [deleteSession, activeSessionId],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background shadow-lg">
      {/* Header bar */}
      <button
        type="button"
        className="flex w-full cursor-pointer items-center justify-between bg-muted/50 px-4 py-2"
        onClick={() => setIsExpanded((prev) => !prev)}
      >
        <div className="flex items-center gap-2 text-sm font-medium">
          <MessageSquare className="size-4" />
          <span>Chat &mdash; {scopeLabel}</span>
          {activeSessionId && sessions.length > 0 && (
            <span className="text-xs text-muted-foreground">
              ({sessions.find((s) => s.id === activeSessionId)?.title})
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="size-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expanded panel */}
      {isExpanded && (
        <>
          {/* Drag handle */}
          <div
            className="flex h-1.5 cursor-row-resize items-center justify-center hover:bg-accent"
            onPointerDown={handleResizePointerDown}
            onPointerMove={handleResizePointerMove}
            onPointerUp={handleResizePointerUp}
          >
            <div className="h-0.5 w-8 rounded-full bg-muted-foreground/30" />
          </div>
        </>
      )}
      {isExpanded && (
        <div className="flex" style={{ height: panelHeight }}>
          {/* Session sidebar */}
          <div className="flex w-48 shrink-0 flex-col border-r bg-muted/30">
            <div className="flex items-center justify-between border-b px-2 py-1.5">
              <span className="text-xs font-medium text-muted-foreground">
                Sessions
              </span>
              <button
                type="button"
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={(e) => {
                  e.stopPropagation();
                  handleNewSession();
                }}
                title="New session"
              >
                <Plus className="size-3.5" />
              </button>
            </div>
            <div className="flex-1 space-y-0.5 overflow-y-auto p-1">
              {sessions.length === 0 && (
                <p className="px-2 py-4 text-center text-xs text-muted-foreground">
                  No sessions yet
                </p>
              )}
              {sessions.map((s) => (
                <SessionListItem
                  key={s.id}
                  session={s}
                  isActive={s.id === activeSessionId}
                  onSelect={() => {
                    setActiveSessionId(s.id);
                  }}
                  onDelete={() => handleDeleteSession(s.id)}
                  onRename={(title) =>
                    renameSession.mutate({ id: s.id, title })
                  }
                />
              ))}
            </div>
          </div>

          {/* Chat area */}
          <div className="flex flex-1 flex-col">
            {/* Message list */}
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Ask a question about your books...
                </p>
              )}
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} message={msg} />
              ))}
              {isStreaming &&
                messages[messages.length - 1]?.role !== "assistant" && (
                  <TypingIndicator />
                )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input bar */}
            <div className="flex items-center gap-2 border-t p-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your books..."
                disabled={isStreaming}
                className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none ring-ring placeholder:text-muted-foreground focus:ring-2 disabled:opacity-50"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={isStreaming || !input.trim()}
                className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-2 text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                title="Send message"
              >
                <Send className="size-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
