import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.book import Book, BookFormat, BookStatus
from app.models.group import Group

_ALLOWED_MIMETYPES: dict[str, BookFormat] = {
    "application/pdf": BookFormat.PDF,
    "application/epub+zip": BookFormat.EPUB,
}


class BookService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, group_id: UUID, title: str, file_path: str) -> Book:
        book = Book(
            group_id=group_id,
            title=title,
            file_path=file_path,
            status=BookStatus.PROCESSING.value,
        )
        self._session.add(book)
        await self._session.commit()
        await self._session.refresh(book)
        return book

    async def get_all(self, group_id: UUID | None = None) -> list[Book]:
        query = select(Book)
        if group_id is not None:
            query = query.where(Book.group_id == group_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, book_id: UUID) -> Book:
        book = await self._session.get(Book, book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )
        return book

    async def update_title(self, book_id: UUID, title: str) -> Book:
        book = await self._session.get(Book, book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
        book.title = title
        await self._session.commit()
        await self._session.refresh(book)
        return book

    async def delete(self, book_id: UUID) -> None:
        book = await self._session.get(Book, book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        file_path = Path(book.file_path)
        file_path.unlink(missing_ok=True)

        await self._session.delete(book)
        await self._session.commit()

    async def upload_and_create(self, group_id: UUID, file: UploadFile) -> Book:
        book_format = _ALLOWED_MIMETYPES.get(file.content_type or "")
        if not book_format:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and EPUB files are supported.",
            )

        book_id = uuid4()
        storage_dir = Path(settings.books_storage_path)
        storage_dir.mkdir(parents=True, exist_ok=True)

        extension = ".pdf" if book_format == BookFormat.PDF else ".epub"
        file_path = storage_dir / f"{book_id}{extension}"

        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicate file
        existing = await self._session.execute(
            select(Book).where(Book.file_hash == file_hash)
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            group = await self._session.get(Group, duplicate.group_id)
            group_name = group.name if group else "Unknown"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This file was already stored in group \"{group_name}\" as \"{duplicate.title}\".",
            )

        file_path.write_bytes(content)

        title = Path(file.filename or "untitled").stem

        book = Book(
            id=book_id,
            group_id=group_id,
            title=title,
            file_path=str(file_path),
            file_hash=file_hash,
            format=book_format.value,
            status=BookStatus.PROCESSING.value,
        )
        self._session.add(book)
        await self._session.commit()
        await self._session.refresh(book)
        return book
