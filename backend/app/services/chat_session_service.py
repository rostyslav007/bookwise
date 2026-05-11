from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate


class ChatSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ChatSessionCreate) -> ChatSession:
        chat_session = ChatSession(
            title=data.title,
            scope=data.scope,
            group_id=UUID(data.group_id) if data.group_id else None,
            book_id=UUID(data.book_id) if data.book_id else None,
        )
        self._session.add(chat_session)
        await self._session.commit()
        await self._session.refresh(chat_session)
        return chat_session

    async def get_all(
        self,
        scope: str | None = None,
        group_id: UUID | None = None,
        book_id: UUID | None = None,
    ) -> list[ChatSession]:
        query = select(ChatSession).order_by(ChatSession.updated_at.desc())
        if scope:
            query = query.where(ChatSession.scope == scope)
        if group_id:
            query = query.where(ChatSession.group_id == group_id)
        if book_id:
            query = query.where(ChatSession.book_id == book_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, session_id: UUID) -> ChatSession:
        query = (
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        result = await self._session.execute(query)
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        return chat_session

    async def update(self, session_id: UUID, data: ChatSessionUpdate) -> ChatSession:
        chat_session = await self._session.get(ChatSession, session_id)
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        chat_session.title = data.title
        await self._session.commit()
        await self._session.refresh(chat_session)
        return chat_session

    async def delete(self, session_id: UUID) -> None:
        chat_session = await self._session.get(ChatSession, session_id)
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        await self._session.delete(chat_session)
        await self._session.commit()

    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
        )
        self._session.add(message)
        # Update session's updated_at
        chat_session = await self._session.get(ChatSession, session_id)
        if chat_session:
            chat_session.updated_at = func.now()
        await self._session.commit()
        await self._session.refresh(message)
        return message
