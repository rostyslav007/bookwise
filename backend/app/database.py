from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Main pool: serves UI/API queries — generous pool for fast responses
engine = create_async_engine(
    settings.database_url,
    pool_size=8,
    max_overflow=4,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# Background pool: for indexing/processing — limited to avoid starving UI queries
_background_engine = create_async_engine(
    settings.database_url,
    pool_size=4,
    max_overflow=2,
)

background_session_factory = async_sessionmaker(_background_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
