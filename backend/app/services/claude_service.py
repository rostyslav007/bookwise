import json
import logging

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a book structure analyst. Your job is to produce a hierarchical "
    "table of contents for a PDF book. Return ONLY valid JSON — no markdown "
    "fences, no commentary. The JSON must be an array of chapter objects."
)

_OUTPUT_SCHEMA_DESCRIPTION = """
Return a JSON array. Each element has:
- "title": string
- "start_page": integer (1-based)
- "end_page": integer (1-based, inclusive)
- "children": array of the same structure (sections/sub-sections), may be empty

Example:
[
  {
    "title": "Chapter 1: Introduction",
    "start_page": 1,
    "end_page": 15,
    "children": [
      {"title": "What is Design Patterns", "start_page": 1, "end_page": 5, "children": []},
      {"title": "Why Use Patterns", "start_page": 6, "end_page": 15, "children": []}
    ]
  }
]
"""


class ClaudeService:
    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate_structure(
        self,
        book_title: str,
        total_pages: int,
        base_toc: list[list[int | str]],
        page_samples: list[dict[str, int | str]],
    ) -> list[dict[str, object]]:
        """Generate detailed hierarchical structure using Claude."""
        user_prompt = self._build_prompt(book_title, total_pages, base_toc, page_samples)

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        return self._parse_response(raw_text)

    def _build_prompt(
        self,
        book_title: str,
        total_pages: int,
        base_toc: list[list[int | str]],
        page_samples: list[dict[str, int | str]],
    ) -> str:
        parts: list[str] = [
            f'Book title: "{book_title}"',
            f"Total pages: {total_pages}",
            "",
            _OUTPUT_SCHEMA_DESCRIPTION,
        ]

        if base_toc:
            toc_lines = [f"  Level {entry[0]}: \"{entry[1]}\" (page {entry[2]})" for entry in base_toc]
            parts.append("Existing table of contents extracted from PDF metadata:")
            parts.append("\n".join(toc_lines))
            parts.append("")
            parts.append(
                "Enrich this table of contents by breaking each chapter into detailed "
                "sections and sub-sections based on the page content provided below."
            )
        else:
            parts.append(
                "No table of contents was found in the PDF metadata. "
                "Analyze the page samples below and generate a complete hierarchical "
                "structure with chapters, sections, and sub-sections."
            )

        if page_samples:
            parts.append("")
            parts.append("Page samples:")
            for sample in page_samples:
                parts.append(f"--- Page {sample['page']} ---")
                parts.append(str(sample["text"]))

        return "\n".join(parts)

    def _parse_response(self, raw_text: str) -> list[dict[str, object]]:
        text = raw_text.strip()
        if text.startswith("```"):
            first_newline = text.index("\n")
            text = text[first_newline + 1 :]
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse Claude response as JSON: %s", text[:500])
            return []

        if not isinstance(result, list):
            logger.error("Claude response is not a list: %s", type(result))
            return []

        return result
