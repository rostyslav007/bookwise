from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchResult, SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])

_embedding_service: EmbeddingService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


@router.get("/", response_model=SearchResult)
async def search_books(
    q: str = Query(..., min_length=1, description="Search query"),
    session: AsyncSession = Depends(get_session),
) -> SearchResult:
    service = SearchService(session, _get_embedding_service())
    return await service.search(q)
