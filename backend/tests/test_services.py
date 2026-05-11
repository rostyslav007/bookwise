from uuid import uuid4

import pytest

from app.models.book import Book, BookStatus
from app.models.group import Group
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.schemas.group import GroupCreate, GroupUpdate
from app.services.book_service import BookService
from app.services.chapter_service import ChapterService
from app.services.group_service import GroupService


# --- GroupService ---


async def test_group_service_create(session):
    service = GroupService(session)

    group = await service.create(GroupCreate(name="svc-test-group"))

    assert group.id is not None
    assert group.name == "svc-test-group"


async def test_group_service_get_all(session):
    service = GroupService(session)
    await service.create(GroupCreate(name="list-group-1"))
    await service.create(GroupCreate(name="list-group-2"))

    groups = await service.get_all()

    names = [g.name for g in groups]
    assert "list-group-1" in names
    assert "list-group-2" in names


async def test_group_service_update(session):
    service = GroupService(session)
    group = await service.create(GroupCreate(name="old-name"))

    updated = await service.update(group.id, GroupUpdate(name="new-name"))

    assert updated.name == "new-name"


async def test_group_service_delete(session):
    service = GroupService(session)
    group = await service.create(GroupCreate(name="to-delete"))

    await service.delete(group.id)

    groups = await service.get_all()
    assert not any(g.id == group.id for g in groups)


async def test_group_service_update_nonexistent_raises(session):
    service = GroupService(session)

    with pytest.raises(Exception):
        await service.update(uuid4(), GroupUpdate(name="nope"))


async def test_group_service_delete_nonexistent_raises(session):
    service = GroupService(session)

    with pytest.raises(Exception):
        await service.delete(uuid4())


# --- BookService ---


async def test_book_service_get_all(session, sample_group):
    service = BookService(session)
    book = Book(
        group_id=sample_group.id,
        title="Service Book",
        file_path="/tmp/svc.pdf",
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.commit()

    books = await service.get_all()

    assert any(b.title == "Service Book" for b in books)


async def test_book_service_get_all_filtered(session, sample_group):
    service = BookService(session)
    book = Book(
        group_id=sample_group.id,
        title="Filtered Book",
        file_path="/tmp/filtered.pdf",
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.commit()

    books = await service.get_all(group_id=sample_group.id)

    assert all(b.group_id == sample_group.id for b in books)
    assert any(b.title == "Filtered Book" for b in books)


async def test_book_service_get_by_id(session, sample_book):
    service = BookService(session)

    book = await service.get_by_id(sample_book.id)

    assert book.id == sample_book.id
    assert book.title == "Test Book"


async def test_book_service_get_by_id_nonexistent_raises(session):
    service = BookService(session)

    with pytest.raises(Exception):
        await service.get_by_id(uuid4())


# --- ChapterService ---


async def test_chapter_service_create(session, sample_book):
    service = ChapterService(session)

    chapter = await service.create(
        sample_book.id,
        ChapterCreate(title="Ch1", start_page=1, end_page=10),
    )

    assert chapter.title == "Ch1"
    assert chapter.book_id == sample_book.id
    assert chapter.level == 0
    assert chapter.order == 0


async def test_chapter_service_create_with_parent(session, sample_book):
    service = ChapterService(session)
    parent = await service.create(
        sample_book.id,
        ChapterCreate(title="Parent", start_page=1, end_page=20),
    )

    child = await service.create(
        sample_book.id,
        ChapterCreate(title="Child", parent_id=parent.id, start_page=1, end_page=10),
    )

    assert child.level == 1
    assert child.parent_id == parent.id


async def test_chapter_service_update(session, sample_book):
    service = ChapterService(session)
    chapter = await service.create(
        sample_book.id,
        ChapterCreate(title="Original", start_page=1, end_page=5),
    )

    updated = await service.update(
        chapter.id,
        ChapterUpdate(title="Modified", end_page=15),
    )

    assert updated.title == "Modified"
    assert updated.end_page == 15
    assert updated.start_page == 1


async def test_chapter_service_delete(session, sample_book):
    service = ChapterService(session)
    chapter = await service.create(
        sample_book.id,
        ChapterCreate(title="Disposable", start_page=1, end_page=5),
    )

    await service.delete(chapter.id)

    with pytest.raises(Exception):
        await service.update(chapter.id, ChapterUpdate(title="Gone"))


async def test_chapter_service_merge(session, sample_book):
    service = ChapterService(session)
    ch1 = await service.create(
        sample_book.id,
        ChapterCreate(title="First", start_page=1, end_page=10),
    )
    ch2 = await service.create(
        sample_book.id,
        ChapterCreate(title="Second", start_page=11, end_page=20),
    )

    merged = await service.merge([ch1.id, ch2.id])

    assert "First" in merged.title
    assert "Second" in merged.title
    assert merged.start_page == 1
    assert merged.end_page == 20
