"""Service for streaming chat responses with tool-use RAG retrieval."""

import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

import anthropic

from app.config import settings
from app.database import async_session_factory
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)

_TOOLS = [
    {
        "name": "search_books",
        "description": (
            "Search the user's book library by concept, pattern, or topic. "
            "Returns ranked results with book title, chapter, page number, snippet, and viewer URL. "
            "Use this for broad questions across the library."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'Observer pattern', 'RAG chunking strategies')",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "explain_from_book",
        "description": (
            "Retrieve chunks from a specific book to explain a concept. "
            "Use when the user references a specific book or page. "
            "Supports page-based retrieval, semantic search, or both. "
            "If the book title is ambiguous, returns a list of matching books — "
            "ask the user to clarify and call again."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "book_title": {
                    "type": "string",
                    "description": "Book name (fuzzy matched, e.g., 'DDIA' or 'Database Internals')",
                },
                "query": {
                    "type": "string",
                    "description": "Concept to explain (e.g., 'hinted handoff', 'B-tree vs LSM-tree')",
                },
                "page_number": {
                    "type": "integer",
                    "description": "Page the user is reading — retrieves nearby chunks",
                },
                "page_range": {
                    "type": "integer",
                    "description": "Pages before/after page_number to include (default: 5)",
                    "default": 5,
                },
                "limit": {
                    "type": "integer",
                    "description": "Max chunks to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["book_title"],
        },
    },
]

_SYSTEM_PROMPT = (
    "You are a knowledgeable assistant helping the user explore their technical book library.\n"
    "You have tools to search books and retrieve specific passages.\n\n"
    "Style: Write in a conversational, flowing prose style — like a knowledgeable colleague explaining "
    "something over coffee. Avoid bullet point lists and rigid structure. Use paragraphs, not headers. "
    "Weave citations naturally into your explanation rather than repeating them before every paragraph.\n\n"
    "When citing content, use markdown links: [Book Title — Chapter Name, p.123](viewer_url)\n"
    "Each tool result includes viewer_url — use it as the link target.\n"
    "If tools return no relevant results, say so and answer from general knowledge.\n"
    "Use tools proactively — don't guess when you can look up the answer in the user's books."
)


def _create_client() -> anthropic.AsyncAnthropic | anthropic.AsyncAnthropicBedrock:
    if settings.aws_bearer_token_bedrock:
        return anthropic.AsyncAnthropicBedrock(
            aws_region=settings.aws_bedrock_region,
            api_key=settings.aws_bearer_token_bedrock,
        )
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _get_model() -> str:
    if settings.aws_bearer_token_bedrock:
        return settings.bedrock_model
    return "claude-sonnet-4-20250514"


_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


class ChatService:
    def __init__(self) -> None:
        self._client = _create_client()
        self._model = _get_model()

    async def _execute_tool(self, name: str, input_args: dict) -> str:
        """Execute a tool call with its own DB session."""
        async with async_session_factory() as session:
            search = SearchService(session, _get_embedding_service())

            if name == "search_books":
                result = await search.search(
                    query=input_args["query"],
                    limit=input_args.get("limit", 10),
                    group_id=self._current_group_id,
                    book_id=self._current_book_id,
                )
                return result.model_dump_json()

            if name == "explain_from_book":
                result = await search.explain_from_book(
                    book_title=input_args["book_title"],
                    query=input_args.get("query"),
                    page_number=input_args.get("page_number"),
                    page_range=input_args.get("page_range", 5),
                    limit=input_args.get("limit", 10),
                )
                return result.model_dump_json()

        return json.dumps({"error": f"Unknown tool: {name}"})

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        scope_label: str,
        group_id: UUID | None = None,
        book_id: UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream Claude's response, handling tool calls transparently."""
        self._current_group_id = group_id
        self._current_book_id = book_id

        system = f"{_SYSTEM_PROMPT}\nScope: {scope_label}"
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        try:
            # Step 1: Let Claude decide which tools to call (single non-streaming round)
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=api_messages,
                tools=_TOOLS,
            )

            tool_calls = [b for b in response.content if b.type == "tool_use"]

            print(f"[CHAT] Step 1 done: stop_reason={response.stop_reason}, "
                  f"tools={[tc.name for tc in tool_calls]}, "
                  f"text_blocks={sum(1 for b in response.content if b.type == 'text')}", flush=True)

            # No tool calls — Claude answered directly, yield text
            if not tool_calls:
                for block in response.content:
                    if block.type == "text" and block.text:
                        yield block.text
                return

            # Step 2: Execute all tool calls
            yield "*Searching your books...*\n\n"

            api_messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tc in tool_calls:
                print(f"[CHAT] Executing tool {tc.name}({tc.input})", flush=True)
                result_json = await self._execute_tool(tc.name, tc.input)
                print(f"[CHAT] Tool {tc.name} returned {len(result_json)} chars", flush=True)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result_json,
                })
            # Step 3: Inject tool results into system prompt, extract page images, stream answer
            context_parts = []
            page_images: list[dict] = []
            for tc, tr in zip(tool_calls, tool_results):
                result_json = tr["content"]
                context_parts.append(f"[{tc.name}]:\n{result_json}")
                # Extract images from tool results
                try:
                    data = json.loads(result_json)
                    for img in data.get("images") or []:
                        page_images.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": img.get("media_type", "image/png"),
                                "data": img["image_base64"],
                            },
                        })
                except (json.JSONDecodeError, KeyError):
                    pass
            context_text = "\n\n".join(context_parts)
            print(f"[CHAT] Extracted {len(page_images)} page images from tool results", flush=True)

            answer_system = (
                f"{system}\n\n"
                f"--- Book excerpts retrieved for this question ---\n"
                f"{context_text}\n"
                f"--- End of excerpts ---\n\n"
                f"Answer using the excerpts above. Do NOT repeat or quote the raw excerpts. "
                f"Do NOT mention that you searched or retrieved anything. Just answer directly."
            )

            # Build user message with optional page images
            user_content: list[dict] | str = messages[-1]["content"]
            if page_images:
                user_content = [
                    {"type": "text", "text": f"Page images from the book for visual reference:"},
                    *page_images,
                    {"type": "text", "text": messages[-1]["content"]},
                ]

            answer_messages = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]
            answer_messages.append({"role": "user", "content": user_content})

            print(f"[CHAT] Step 3: streaming final answer with {len(tool_results)} tool results", flush=True)

            async with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=answer_system,
                messages=answer_messages,
            ) as stream:
                async for text_chunk in stream.text_stream:
                    yield text_chunk

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"\n\n⚠️ **Error:** {type(e).__name__}: {e}"
