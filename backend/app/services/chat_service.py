"""Service for streaming chat responses with tool-use RAG retrieval."""

import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

import anthropic

from app.config import settings
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


class ChatService:
    def __init__(self, search_service: SearchService) -> None:
        self._search = search_service
        self._client = _create_client()
        self._model = _get_model()

    async def _execute_tool(self, name: str, input_args: dict) -> str:
        """Execute a tool call and return the JSON result."""
        if name == "search_books":
            result = await self._search.search(
                query=input_args["query"],
                limit=input_args.get("limit", 10),
                group_id=self._current_group_id,
                book_id=self._current_book_id,
            )
            return result.model_dump_json()

        if name == "explain_from_book":
            result = await self._search.explain_from_book(
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
            # Allow up to 3 tool-use rounds before forcing a final text response
            for _ in range(3):
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=system,
                    messages=api_messages,
                    tools=_TOOLS,
                )

                # Collect tool calls and text from this response
                tool_calls = []
                for block in response.content:
                    if block.type == "text" and block.text:
                        yield block.text
                    elif block.type == "tool_use":
                        tool_calls.append(block)

                if not tool_calls:
                    return

                # Execute tools and add results to conversation
                api_messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for tc in tool_calls:
                    result_json = await self._execute_tool(tc.name, tc.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": result_json,
                    })
                api_messages.append({"role": "user", "content": tool_results})

            # Final round: stream the text response
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=api_messages,
            ) as stream:
                async for text_chunk in stream.text_stream:
                    yield text_chunk

        except anthropic.BadRequestError as e:
            error_msg = str(e)
            if "credit balance" in error_msg.lower():
                yield (
                    "⚠️ **Claude API credits required.** "
                    "The chat feature uses the Claude API which requires prepaid credits "
                    "(separate from your Claude Code subscription). "
                    "Add credits at [console.anthropic.com](https://console.anthropic.com) → Plans & Billing."
                )
            else:
                yield f"⚠️ **API error:** {error_msg}"
        except anthropic.AuthenticationError:
            yield (
                "⚠️ **Invalid API key.** "
                "Set a valid `ANTHROPIC_API_KEY` or `AWS_BEARER_TOKEN_BEDROCK` in your `.env` file."
            )
        except Exception:
            logger.exception("Chat stream error")
            yield "⚠️ **Error:** Something went wrong. Please try again."
