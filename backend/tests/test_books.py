import io
import os
import tempfile
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


async def test_upload_pdf_returns_201(client, sample_group, sample_pdf_bytes):
    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        response = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "test"
    assert body["status"] == "processing"
    assert body["group_id"] == str(sample_group.id)


async def test_upload_non_pdf_returns_400(client, sample_group):
    response = await client.post(
        "/api/v1/books/",
        data={"group_id": str(sample_group.id)},
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


async def test_list_books(client, sample_book):
    response = await client.get("/api/v1/books/")

    assert response.status_code == 200
    books = response.json()
    assert any(b["id"] == str(sample_book.id) for b in books)


async def test_list_books_filter_by_group(client, sample_book, sample_group):
    response = await client.get(
        "/api/v1/books/", params={"group_id": str(sample_group.id)}
    )

    assert response.status_code == 200
    books = response.json()
    assert all(b["group_id"] == str(sample_group.id) for b in books)
    assert any(b["id"] == str(sample_book.id) for b in books)


async def test_list_books_filter_by_other_group_returns_empty(client, sample_book):
    other_group_id = str(uuid4())

    response = await client.get(
        "/api/v1/books/", params={"group_id": other_group_id}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_get_book_by_id(client, sample_book):
    response = await client.get(f"/api/v1/books/{sample_book.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(sample_book.id)
    assert body["title"] == "Test Book"


async def test_get_nonexistent_book_returns_404(client):
    fake_id = str(uuid4())

    response = await client.get(f"/api/v1/books/{fake_id}")

    assert response.status_code == 404


async def test_delete_book(client, sample_pdf_bytes, sample_group):
    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        upload_response = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert upload_response.status_code == 201
    book = upload_response.json()
    book_id = book["id"]
    file_path = book["file_path"]
    assert os.path.exists(file_path)

    delete_response = await client.delete(f"/api/v1/books/{book_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/books/{book_id}")
    assert get_response.status_code == 404

    assert not os.path.exists(file_path)


async def test_delete_nonexistent_book_returns_404(client):
    fake_id = str(uuid4())

    response = await client.delete(f"/api/v1/books/{fake_id}")

    assert response.status_code == 404


async def test_serve_book_pdf(client, session, sample_group, sample_pdf_bytes):
    from app.models.book import Book, BookStatus

    book = Book(
        group_id=sample_group.id,
        title="Serve PDF Test",
        file_path="placeholder",
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
        response = await client.get(f"/api/v1/books/{book.id}/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
    finally:
        if os.path.exists(relative_path):
            os.remove(relative_path)


async def test_serve_nonexistent_book_pdf_returns_404(client):
    fake_id = str(uuid4())

    response = await client.get(f"/api/v1/books/{fake_id}/pdf")

    assert response.status_code == 404
