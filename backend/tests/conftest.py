import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator
from uuid import uuid4

import fitz
import httpx
import pytest
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app
from app.models.book import Book, BookStatus
from app.models.chapter import Chapter  # noqa: F401
from app.models.chunk import ChunkEmbedding  # noqa: F401
from app.models.chat import ChatMessage, ChatSession  # noqa: F401
from app.models.group import Group  # noqa: F401

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/books_test",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def client(session):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test content for embedding")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def sample_pdf_path(sample_pdf_bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(sample_pdf_bytes)
        return f.name


@pytest.fixture
async def sample_group(session) -> Group:
    group = Group(name=f"test-group-{uuid4().hex[:8]}")
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


@pytest.fixture
async def sample_book(session, sample_group) -> Book:
    book = Book(
        group_id=sample_group.id,
        title="Test Book",
        file_path="/tmp/fake.pdf",
        status=BookStatus.READY.value,
    )
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book
