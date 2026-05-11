import os
import tempfile
from uuid import uuid4

import pytest

from app.models.book import Book, BookStatus


@pytest.fixture
async def created_group(client):
    response = await client.post("/api/v1/groups/", json={"name": "Fiction"})
    assert response.status_code == 201
    return response.json()


async def test_create_group(client):
    response = await client.post("/api/v1/groups/", json={"name": "Science"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Science"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_list_groups(client, created_group):
    response = await client.get("/api/v1/groups/")

    assert response.status_code == 200
    groups = response.json()
    assert any(g["id"] == created_group["id"] for g in groups)


async def test_update_group(client, created_group):
    group_id = created_group["id"]

    response = await client.put(
        f"/api/v1/groups/{group_id}", json={"name": "Updated Fiction"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Fiction"
    assert body["id"] == group_id


async def test_delete_group(client, created_group):
    group_id = created_group["id"]

    response = await client.delete(f"/api/v1/groups/{group_id}")
    assert response.status_code == 204

    list_response = await client.get("/api/v1/groups/")
    groups = list_response.json()
    assert not any(g["id"] == group_id for g in groups)


async def test_update_nonexistent_group_returns_404(client):
    fake_id = str(uuid4())

    response = await client.put(
        f"/api/v1/groups/{fake_id}", json={"name": "Ghost"}
    )

    assert response.status_code == 404


async def test_delete_nonexistent_group_returns_404(client):
    fake_id = str(uuid4())

    response = await client.delete(f"/api/v1/groups/{fake_id}")

    assert response.status_code == 404


async def test_delete_group_cascades_to_books(client, session):
    # Create a group via API
    group_response = await client.post("/api/v1/groups/", json={"name": "Cascade Test"})
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Create a fake PDF file on disk
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 fake content")
        pdf_path = f.name

    # Create a book directly via ORM (avoids background processing)
    book = Book(
        group_id=group_id,
        title="Cascade Book",
        file_path=pdf_path,
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.commit()
    await session.refresh(book)
    book_id = str(book.id)

    assert os.path.exists(pdf_path)

    # Delete the group
    delete_response = await client.delete(f"/api/v1/groups/{group_id}")
    assert delete_response.status_code == 204

    # Verify book is gone
    books_response = await client.get("/api/v1/books/")
    assert books_response.status_code == 200
    assert not any(b["id"] == book_id for b in books_response.json())

    # Verify PDF file is gone from disk
    assert not os.path.exists(pdf_path)
