from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class ChatSessionCreate(BaseModel):
    title: str
    scope: str
    group_id: str | None = None
    book_id: str | None = None


class ChatSessionUpdate(BaseModel):
    title: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    scope: str
    group_id: UUID | None
    book_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[ChatMessageResponse]


class ChatStreamRequest(BaseModel):
    session_id: str
    message: str
