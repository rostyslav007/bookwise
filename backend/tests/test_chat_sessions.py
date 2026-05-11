"""Tests for chat session CRUD endpoints."""

from uuid import uuid4

import pytest


async def test_create_session(client, sample_group):
    response = await client.post(
        "/api/v1/chat/sessions/",
        json={
            "title": "Test Session",
            "scope": "group",
            "group_id": str(sample_group.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Test Session"
    assert body["scope"] == "group"
    assert body["group_id"] == str(sample_group.id)
    assert body["book_id"] is None


async def test_create_session_library_scope(client):
    response = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Library Chat", "scope": "library"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["scope"] == "library"
    assert body["group_id"] is None
    assert body["book_id"] is None


async def test_create_session_book_scope(client, sample_book):
    response = await client.post(
        "/api/v1/chat/sessions/",
        json={
            "title": "Book Chat",
            "scope": "book",
            "book_id": str(sample_book.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["scope"] == "book"
    assert body["book_id"] == str(sample_book.id)


async def test_list_sessions_empty(client):
    response = await client.get("/api/v1/chat/sessions/")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_sessions(client, sample_group):
    await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Session 1", "scope": "group", "group_id": str(sample_group.id)},
    )
    await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Session 2", "scope": "group", "group_id": str(sample_group.id)},
    )

    response = await client.get("/api/v1/chat/sessions/")

    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) >= 2
    titles = [s["title"] for s in sessions]
    assert "Session 1" in titles
    assert "Session 2" in titles


async def test_list_sessions_filter_by_scope(client, sample_group):
    await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Library Session", "scope": "library"},
    )
    await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Group Session", "scope": "group", "group_id": str(sample_group.id)},
    )

    response = await client.get("/api/v1/chat/sessions/", params={"scope": "library"})

    assert response.status_code == 200
    sessions = response.json()
    assert all(s["scope"] == "library" for s in sessions)


async def test_list_sessions_filter_by_group(client, sample_group):
    await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Grouped", "scope": "group", "group_id": str(sample_group.id)},
    )

    response = await client.get(
        "/api/v1/chat/sessions/", params={"group_id": str(sample_group.id)}
    )

    assert response.status_code == 200
    sessions = response.json()
    assert all(s["group_id"] == str(sample_group.id) for s in sessions)


async def test_get_session_detail(client):
    create_resp = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Detail Test", "scope": "library"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/chat/sessions/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == session_id
    assert body["title"] == "Detail Test"
    assert body["messages"] == []


async def test_get_session_detail_not_found(client):
    fake_id = str(uuid4())

    response = await client.get(f"/api/v1/chat/sessions/{fake_id}")

    assert response.status_code == 404


async def test_update_session_title(client):
    create_resp = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Old Title", "scope": "library"},
    )
    session_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/chat/sessions/{session_id}",
        json={"title": "New Title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


async def test_update_session_not_found(client):
    fake_id = str(uuid4())

    response = await client.put(
        f"/api/v1/chat/sessions/{fake_id}",
        json={"title": "Nope"},
    )

    assert response.status_code == 404


async def test_delete_session(client):
    create_resp = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "To Delete", "scope": "library"},
    )
    session_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/chat/sessions/{session_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/chat/sessions/{session_id}")
    assert get_resp.status_code == 404


async def test_delete_session_not_found(client):
    fake_id = str(uuid4())

    response = await client.delete(f"/api/v1/chat/sessions/{fake_id}")

    assert response.status_code == 404


async def test_delete_session_cascades_messages(client, session):
    from app.models.chat import ChatMessage
    from sqlalchemy import select

    create_resp = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Cascade Test", "scope": "library"},
    )
    session_id = create_resp.json()["id"]

    # Add messages directly
    from uuid import UUID
    from app.services.chat_session_service import ChatSessionService

    svc = ChatSessionService(session)
    await svc.add_message(UUID(session_id), "user", "Hello")
    await svc.add_message(UUID(session_id), "assistant", "Hi there")

    # Verify messages exist
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.session_id == UUID(session_id))
    )
    assert len(result.scalars().all()) == 2

    # Delete session
    delete_resp = await client.delete(f"/api/v1/chat/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Verify messages are gone
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.session_id == UUID(session_id))
    )
    assert len(result.scalars().all()) == 0


async def test_sessions_ordered_by_updated_at_desc(client):
    resp1 = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "First", "scope": "library"},
    )
    resp2 = await client.post(
        "/api/v1/chat/sessions/",
        json={"title": "Second", "scope": "library"},
    )

    response = await client.get("/api/v1/chat/sessions/")
    sessions = response.json()
    titles = [s["title"] for s in sessions]

    # Most recently created should come first
    assert titles.index("Second") < titles.index("First")
