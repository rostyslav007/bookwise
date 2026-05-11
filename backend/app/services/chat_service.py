"""Service for streaming chat responses with RAG-based context retrieval."""

import logging
from collections.abc import AsyncGenerator
from uuid import UUID

import anthropic

from app.config import settings
from app.services.search_service import SearchResult, SearchService

logger = logging.getLogger(__name__)


def _create_client() -> anthropic.AsyncAnthropic | anthropic.AsyncAnthropicBedrock:
    """Create the appropriate Anthropic client based on config."""
    if settings.aws_bearer_token_bedrock:
        return anthropic.AsyncAnthropicBedrock(
            aws_region=settings.aws_bedrock_region,
            api_key=settings.aws_bearer_token_bedrock,
        )
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _get_model() -> str:
    """Get the model ID based on which client is used."""
    if settings.aws_bearer_token_bedrock:
        return settings.bedrock_model
    return "claude-sonnet-4-20250514"


class ChatService:
    def __init__(self, search_service: SearchService) -> None:
        self._search = search_service
        self._client = _create_client()
        self._model = _get_model()

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        scope_label: str,
        group_id: UUID | None = None,
        book_id: UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """Retrieve relevant chunks and stream Claude's response."""
        latest_query = messages[-1]["content"]

        limit = 10 if (group_id or book_id) else 15
        results = await self._search.search(
            latest_query, limit=limit, group_id=group_id, book_id=book_id
        )

        context_text = self._format_context(results)
        system_prompt = (
            f"You are a knowledgeable assistant helping the user explore their technical book library.\n"
            f"Scope: {scope_label}\n\n"
            f"Use the following book excerpts to answer the user's question. "
            f"When citing content from the excerpts, use markdown links in this exact format:\n"
            f"[Book Title — Chapter Name, p.123](viewer_url)\n"
            f"Each excerpt below includes a viewer_url — use it as the link target.\n"
            f"If the excerpts don't contain relevant information, say so and answer from general knowledge.\n\n"
            f"---\n{context_text}\n---"
        )

        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
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
                "Set a valid `ANTHROPIC_API_KEY` in your `.env` file."
            )
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"⚠️ **Error:** {e}"

    @staticmethod
    def _format_context(results: SearchResult) -> str:
        if not results.results:
            return "No relevant excerpts found in the library."

        parts: list[str] = []
        for hit in results.results:
            parts.append(
                f"**{hit.book_title}** — {hit.chapter_title} (p.{hit.page_number})\n"
                f"viewer_url: {hit.viewer_url}\n"
                f"{hit.snippet}\n"
            )
        return "\n".join(parts)
