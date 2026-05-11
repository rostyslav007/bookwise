import logging

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

logger = logging.getLogger(__name__)


class EpubParserService:
    """Parses EPUB files to extract metadata, TOC, and chapter text."""

    def extract_metadata(self, file_path: str) -> dict[str, str | None]:
        """Extract title and author from EPUB metadata."""
        book = epub.read_epub(file_path, options={"ignore_ncx": True})
        title = book.get_metadata("DC", "title")
        author = book.get_metadata("DC", "creator")
        return {
            "title": title[0][0] if title else None,
            "author": author[0][0] if author else None,
        }

    def extract_toc_and_texts(self, file_path: str) -> list[dict[str, str | int]]:
        """Extract chapters with their text content from EPUB.

        Returns list of dicts with keys: title, text, order, href.
        Each entry represents a chapter/section from the spine.
        """
        book = epub.read_epub(file_path, options={"ignore_ncx": True})

        toc_map = self._build_toc_map(book)

        chapters: list[dict[str, str | int]] = []
        order = 0
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            text = self._html_to_text(item.get_content())
            if not text.strip():
                continue

            href = item.get_name()
            title = toc_map.get(href, f"Section {order + 1}")

            chapters.append({
                "title": title,
                "text": text,
                "html": item.get_content().decode("utf-8", errors="replace"),
                "order": order,
                "href": href,
            })
            order += 1

        return chapters

    def extract_chapter_text(self, file_path: str, chapter_href: str) -> str:
        """Extract text from a specific chapter by href."""
        book = epub.read_epub(file_path, options={"ignore_ncx": True})
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            if item.get_name() == chapter_href:
                return self._html_to_text(item.get_content())
        return ""

    @staticmethod
    def _build_toc_map(book: epub.EpubBook) -> dict[str, str]:
        """Build a mapping from href to title using the EPUB TOC."""
        toc_map: dict[str, str] = {}
        for item in book.toc:
            if isinstance(item, epub.Link):
                href = item.href.split("#")[0]
                toc_map[href] = item.title
            elif isinstance(item, tuple) and len(item) >= 2:
                section = item[0]
                if isinstance(section, epub.Link):
                    href = section.href.split("#")[0]
                    toc_map[href] = section.title
        return toc_map

    @staticmethod
    def _html_to_text(content: bytes) -> str:
        """Convert HTML content to plain text."""
        soup = BeautifulSoup(content, "html.parser")
        return soup.get_text(separator="\n", strip=True)
