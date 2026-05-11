from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChapterCreate(BaseModel):
    title: str
    parent_id: UUID | None = None
    start_page: int
    end_page: int


class ChapterUpdate(BaseModel):
    title: str | None = None
    start_page: int | None = None
    end_page: int | None = None


class ChapterMergeRequest(BaseModel):
    chapter_ids: list[UUID]  # exactly 2 adjacent chapters


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    book_id: UUID
    parent_id: UUID | None
    title: str
    level: int
    order: int
    start_page: int
    end_page: int
    created_at: datetime
    children: list["ChapterResponse"] = Field(default_factory=list)


ChapterResponse.model_rebuild()
