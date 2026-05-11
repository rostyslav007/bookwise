"""Tests for ChatSessionService."""

from uuid import uuid4

import pytest

from app.models.chat import ChatSession
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate
from app.services.chat_session_service import ChatSessionService


async def test_create_session(session, sample_group):
    service = ChatSessionService(session)

    chat_session = await service.create(
        ChatSessionCreate(
            title="Test",
            scope="group",
            group_id=str(sample_group.id),
        )
    )

    assert chat_session.id is not None
    assert chat_session.title == "Test"
    assert chat_session.scope == "group"
    assert chat_session.group_id == sample_group.id


async def test_create_session_library(session):
    service = ChatSessionService(session)

    chat_session = await service.create(
        ChatSessionCreate(title="Lib", scope="library")
    )

    assert chat_session.group_id is None
    assert chat_session.book_id is None


async def test_get_all(session):
    service = ChatSessionService(session)
    await service.create(ChatSessionCreate(title="A", scope="library"))
    await service.create(ChatSessionCreate(title="B", scope="library"))

    sessions = await service.get_all()

    assert len(sessions) >= 2


async def test_get_all_filter_scope(session, sample_group):
    service = ChatSessionService(session)
    await service.create(ChatSessionCreate(title="Lib", scope="library"))
    await service.create(
        ChatSessionCreate(title="Grp", scope="group", group_id=str(sample_group.id))
    )

    library_sessions = await service.get_all(scope="library")

    assert all(s.scope == "library" for s in library_sessions)


async def test_get_all_filter_group(session, sample_group):
    service = ChatSessionService(session)
    await service.create(
        ChatSessionCreate(title="G", scope="group", group_id=str(sample_group.id))
    )

    sessions = await service.get_all(group_id=sample_group.id)

    assert all(s.group_id == sample_group.id for s in sessions)


async def test_get_all_filter_book(session, sample_book):
    service = ChatSessionService(session)
    await service.create(
        ChatSessionCreate(title="B", scope="book", book_id=str(sample_book.id))
    )

    sessions = await service.get_all(book_id=sample_book.id)

    assert all(s.book_id == sample_book.id for s in sessions)


async def test_get_by_id(session):
    service = ChatSessionService(session)
    created = await service.create(ChatSessionCreate(title="Find Me", scope="library"))

    found = await service.get_by_id(created.id)

    assert found.id == created.id
    assert found.title == "Find Me"


async def test_get_by_id_not_found(session):
    service = ChatSessionService(session)

    with pytest.raises(Exception):
        await service.get_by_id(uuid4())


async def test_update(session):
    service = ChatSessionService(session)
    created = await service.create(ChatSessionCreate(title="Old", scope="library"))

    updated = await service.update(created.id, ChatSessionUpdate(title="New"))

    assert updated.title == "New"


async def test_update_not_found(session):
    service = ChatSessionService(session)

    with pytest.raises(Exception):
        await service.update(uuid4(), ChatSessionUpdate(title="Nope"))


async def test_delete(session):
    service = ChatSessionService(session)
    created = await service.create(ChatSessionCreate(title="Del", scope="library"))

    await service.delete(created.id)

    with pytest.raises(Exception):
        await service.get_by_id(created.id)


async def test_delete_not_found(session):
    service = ChatSessionService(session)

    with pytest.raises(Exception):
        await service.delete(uuid4())


async def test_add_message(session):
    service = ChatSessionService(session)
    chat_session = await service.create(
        ChatSessionCreate(title="Msg Test", scope="library")
    )

    message = await service.add_message(chat_session.id, "user", "Hello")

    assert message.role == "user"
    assert message.content == "Hello"
    assert message.session_id == chat_session.id


async def test_add_message_persists_in_detail(session):
    service = ChatSessionService(session)
    chat_session = await service.create(
        ChatSessionCreate(title="Persist", scope="library")
    )

    await service.add_message(chat_session.id, "user", "Question?")
    await service.add_message(chat_session.id, "assistant", "Answer!")

    detail = await service.get_by_id(chat_session.id)

    assert len(detail.messages) == 2
    assert detail.messages[0].role == "user"
    assert detail.messages[0].content == "Question?"
    assert detail.messages[1].role == "assistant"
    assert detail.messages[1].content == "Answer!"
