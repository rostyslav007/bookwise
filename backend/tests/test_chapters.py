from uuid import uuid4

import pytest


@pytest.fixture
async def created_chapter(client, sample_book):
    response = await client.post(
        f"/api/v1/books/{sample_book.id}/chapters",
        json={"title": "Chapter 1", "start_page": 1, "end_page": 10},
    )
    assert response.status_code == 201
    return response.json()


async def test_create_chapter(client, sample_book):
    response = await client.post(
        f"/api/v1/books/{sample_book.id}/chapters",
        json={"title": "Introduction", "start_page": 1, "end_page": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Introduction"
    assert body["book_id"] == str(sample_book.id)
    assert body["start_page"] == 1
    assert body["end_page"] == 5
    assert body["level"] == 0
    assert body["parent_id"] is None


async def test_create_child_chapter(client, sample_book, created_chapter):
    response = await client.post(
        f"/api/v1/books/{sample_book.id}/chapters",
        json={
            "title": "Section 1.1",
            "parent_id": created_chapter["id"],
            "start_page": 1,
            "end_page": 5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 1
    assert body["parent_id"] == created_chapter["id"]


async def test_list_book_chapters(client, sample_book, created_chapter):
    response = await client.get(f"/api/v1/books/{sample_book.id}/chapters")

    assert response.status_code == 200
    chapters = response.json()
    assert len(chapters) >= 1
    assert any(c["id"] == created_chapter["id"] for c in chapters)


async def test_update_chapter(client, created_chapter):
    chapter_id = created_chapter["id"]

    response = await client.put(
        f"/api/v1/chapters/{chapter_id}",
        json={"title": "Renamed Chapter", "start_page": 2, "end_page": 15},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed Chapter"
    assert body["start_page"] == 2
    assert body["end_page"] == 15


async def test_update_chapter_partial(client, created_chapter):
    chapter_id = created_chapter["id"]

    response = await client.put(
        f"/api/v1/chapters/{chapter_id}",
        json={"title": "Only Title Changed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Only Title Changed"
    assert body["start_page"] == created_chapter["start_page"]


async def test_delete_chapter(client, created_chapter):
    chapter_id = created_chapter["id"]

    response = await client.delete(f"/api/v1/chapters/{chapter_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_chapter_returns_404(client):
    fake_id = str(uuid4())

    response = await client.delete(f"/api/v1/chapters/{fake_id}")

    assert response.status_code == 404


async def test_merge_chapters(client, sample_book):
    resp1 = await client.post(
        f"/api/v1/books/{sample_book.id}/chapters",
        json={"title": "Part A", "start_page": 1, "end_page": 10},
    )
    resp2 = await client.post(
        f"/api/v1/books/{sample_book.id}/chapters",
        json={"title": "Part B", "start_page": 11, "end_page": 20},
    )
    chapter_a = resp1.json()
    chapter_b = resp2.json()

    response = await client.post(
        "/api/v1/chapters/merge",
        json={"chapter_ids": [chapter_a["id"], chapter_b["id"]]},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Part A" in body["title"]
    assert "Part B" in body["title"]
    assert body["start_page"] == 1
    assert body["end_page"] == 20


async def test_merge_requires_exactly_two_chapters(client, created_chapter):
    response = await client.post(
        "/api/v1/chapters/merge",
        json={"chapter_ids": [created_chapter["id"]]},
    )

    assert response.status_code == 400
