from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.books import router as books_router
from app.routers.chapters import router as chapters_router
from app.routers.chat import router as chat_router
from app.routers.groups import router as groups_router
from app.routers.search import router as search_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Reset any books stuck in "processing" from a previous interrupted run
    from app.database import async_session_factory
    from sqlalchemy import update
    from app.models.book import Book, BookStatus

    async with async_session_factory() as session:
        result = await session.execute(
            update(Book)
            .where(Book.status == BookStatus.PROCESSING.value)
            .values(status=BookStatus.READY.value)
        )
        if result.rowcount:
            await session.commit()
            import logging
            logging.getLogger(__name__).info("Reset %d stuck processing books on startup", result.rowcount)

    yield


app = FastAPI(title="Bookwise", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(groups_router)
app.include_router(books_router)
app.include_router(chapters_router)
app.include_router(search_router)
app.include_router(chat_router)


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
