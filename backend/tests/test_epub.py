import io
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from ebooklib import epub

from app.services.epub_parser_service import EpubParserService


def create_test_epub(num_chapters: int = 1) -> bytes:
    """Create a minimal valid EPUB file in memory."""
    book = epub.EpubBook()
    book.set_identifier("test-id")
    book.set_title("Test EPUB Book")
    book.set_language("en")
    book.add_author("Test Author")

    chapters = []
    toc = []
    for i in range(1, num_chapters + 1):
        ch = epub.EpubHtml(
            title=f"Chapter {i}", file_name=f"ch{i}.xhtml", lang="en"
        )
        ch.content = (
            f"<html><body><h1>Chapter {i}</h1>"
            f"<p>This is the content of chapter {i} about the Observer pattern.</p>"
            f"</body></html>"
        )
        book.add_item(ch)
        chapters.append(ch)
        toc.append(epub.Link(f"ch{i}.xhtml", f"Chapter {i}", f"ch{i}"))

    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        epub.write_epub(f.name, book)
        data = open(f.name, "rb").read()
    os.unlink(f.name)
    return data


@pytest.fixture
def sample_epub_bytes() -> bytes:
    return create_test_epub(num_chapters=1)


@pytest.fixture
def sample_epub_path(sample_epub_bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        f.write(sample_epub_bytes)
        return f.name


async def test_upload_epub_accepted(client, sample_group):
    epub_bytes = create_test_epub()

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        response = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={
                "file": ("test.epub", io.BytesIO(epub_bytes), "application/epub+zip")
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["format"] == "epub"
    assert body["status"] == "processing"
    assert body["group_id"] == str(sample_group.id)


async def test_upload_invalid_format_rejected(client, sample_group):
    response = await client.post(
        "/api/v1/books/",
        data={"group_id": str(sample_group.id)},
        files={"file": ("test.txt", io.BytesIO(b"not a book"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF and EPUB files are supported."


async def test_epub_parser_extract_metadata(sample_epub_path):
    service = EpubParserService()
    metadata = service.extract_metadata(sample_epub_path)

    assert metadata["title"] == "Test EPUB Book"
    assert metadata["author"] == "Test Author"

    os.unlink(sample_epub_path)


async def test_epub_parser_extract_chapters():
    epub_bytes = create_test_epub(num_chapters=2)

    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        f.write(epub_bytes)
        path = f.name

    try:
        service = EpubParserService()
        chapters = service.extract_toc_and_texts(path)

        assert len(chapters) >= 2
        assert any("Chapter 1" in ch["title"] for ch in chapters)
        assert any("Chapter 2" in ch["title"] for ch in chapters)
        for ch in chapters:
            assert len(ch["text"]) > 0
    finally:
        os.unlink(path)


async def test_serve_epub_file(client, session, sample_group):
    from app.models.book import Book, BookFormat, BookStatus

    epub_bytes = create_test_epub()

    book = Book(
        group_id=sample_group.id,
        title="Serve EPUB Test",
        file_path="placeholder",
        format=BookFormat.EPUB.value,
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.commit()
    await session.refresh(book)

    relative_path = f"data/books/{book.id}.epub"
    book.file_path = relative_path
    await session.commit()

    os.makedirs(os.path.dirname(relative_path), exist_ok=True)
    with open(relative_path, "wb") as f:
        f.write(epub_bytes)

    try:
        response = await client.get(f"/api/v1/books/{book.id}/file")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/epub+zip"
        assert len(response.content) > 0
    finally:
        if os.path.exists(relative_path):
            os.remove(relative_path)


async def test_serve_pdf_file(client, session, sample_group, sample_pdf_bytes):
    from app.models.book import Book, BookFormat, BookStatus

    book = Book(
        group_id=sample_group.id,
        title="Serve PDF Test",
        file_path="placeholder",
        format=BookFormat.PDF.value,
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.commit()
    await session.refresh(book)

    relative_path = f"data/books/{book.id}.pdf"
    book.file_path = relative_path
    await session.commit()

    os.makedirs(os.path.dirname(relative_path), exist_ok=True)
    with open(relative_path, "wb") as f:
        f.write(sample_pdf_bytes)

    try:
        response = await client.get(f"/api/v1/books/{book.id}/file")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
    finally:
        if os.path.exists(relative_path):
            os.remove(relative_path)
