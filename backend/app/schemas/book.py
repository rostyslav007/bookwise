from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BookUpdate(BaseModel):
    title: str


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    title: str
    author: str | None
    file_path: str
    page_count: int | None
    format: str
    status: str
    created_at: datetime
    updated_at: datetime
