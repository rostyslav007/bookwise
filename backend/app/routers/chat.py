"""Chat endpoints: session CRUD + streaming SSE responses powered by RAG."""

import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.database import get_session
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    ChatStreamRequest,
)
from app.services.chat_service import ChatService
from app.services.chat_session_service import ChatSessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# --- Session CRUD ---


@router.post(
    "/sessions/",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    data: ChatSessionCreate,
    session: AsyncSession = Depends(get_session),
) -> ChatSessionResponse:
    service = ChatSessionService(session)
    chat_session = await service.create(data)
    return ChatSessionResponse.model_validate(chat_session)


@router.get("/sessions/", response_model=list[ChatSessionResponse])
async def list_sessions(
    scope: str | None = Query(None),
    group_id: str | None = Query(None),
    book_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[ChatSessionResponse]:
    service = ChatSessionService(session)
    sessions = await service.get_all(
        scope=scope,
        group_id=UUID(group_id) if group_id else None,
        book_id=UUID(book_id) if book_id else None,
    )
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_detail(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ChatSessionDetailResponse:
    service = ChatSessionService(session)
    chat_session = await service.get_by_id(session_id)
    return ChatSessionDetailResponse.model_validate(chat_session)


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: UUID,
    data: ChatSessionUpdate,
    session: AsyncSession = Depends(get_session),
) -> ChatSessionResponse:
    service = ChatSessionService(session)
    chat_session = await service.update(session_id, data)
    return ChatSessionResponse.model_validate(chat_session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = ChatSessionService(session)
    await service.delete(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Streaming chat (persists messages) ---


@router.post("/stream/")
async def chat_stream(
    request: ChatStreamRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    session_service = ChatSessionService(session)
    session_id = UUID(request.session_id)

    # Load session with history
    chat_session = await session_service.get_by_id(session_id)

    # Persist user message
    await session_service.add_message(session_id, "user", request.message)

    # Build messages list from history + new message
    messages = [
        {"role": m.role, "content": m.content} for m in chat_session.messages
    ]
    messages.append({"role": "user", "content": request.message})

    # Determine scope label
    scope_labels = {
        "library": "All books in library",
        "group": f"Group: {chat_session.group_id}",
        "book": f"Book: {chat_session.book_id}",
    }
    scope_label = scope_labels.get(chat_session.scope, "All books")

    chat_service = ChatService()

    async def event_stream() -> AsyncGenerator[str, None]:
        assistant_content = ""
        try:
            async for chunk in chat_service.stream_response(
                messages=messages,
                scope_label=scope_label,
                group_id=chat_session.group_id,
                book_id=chat_session.book_id,
            ):
                assistant_content += chunk
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception:
            logger.exception("Chat stream error for session %s", session_id)
        finally:
            if assistant_content:
                try:
                    await session_service.add_message(
                        session_id, "assistant", assistant_content
                    )
                except Exception:
                    logger.exception("Failed to persist assistant message for session %s", session_id)
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
