"""Tests for duplicate file upload detection."""

import io

from unittest.mock import AsyncMock, patch


async def test_duplicate_upload_returns_409(client, sample_group, sample_pdf_bytes):
    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        first_resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("book.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert first_resp.status_code == 201

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        second_resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("book.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert second_resp.status_code == 409
    detail = second_resp.json()["detail"]
    assert "already stored" in detail


async def test_duplicate_upload_shows_group_name(client, sample_group, sample_pdf_bytes):
    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("mybook.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("mybook.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    detail = resp.json()["detail"]
    assert sample_group.name in detail
    assert "mybook" in detail


async def test_duplicate_across_groups_returns_409(client, session, sample_pdf_bytes):
    from app.models.group import Group

    group_a = Group(name="group-a-dup-test")
    group_b = Group(name="group-b-dup-test")
    session.add(group_a)
    session.add(group_b)
    await session.commit()
    await session.refresh(group_a)
    await session.refresh(group_b)

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        first_resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(group_a.id)},
            files={"file": ("book.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert first_resp.status_code == 201

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        second_resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(group_b.id)},
            files={"file": ("book.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert second_resp.status_code == 409
    detail = second_resp.json()["detail"]
    assert "group-a-dup-test" in detail


async def test_different_files_upload_fine(client, sample_group, sample_pdf_bytes):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Different content entirely")
    different_pdf = doc.tobytes()
    doc.close()

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        first_resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("book1.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    assert first_resp.status_code == 201

    with patch("app.routers.books._run_processing", new_callable=AsyncMock):
        second_resp = await client.post(
            "/api/v1/books/",
            data={"group_id": str(sample_group.id)},
            files={"file": ("book2.pdf", io.BytesIO(different_pdf), "application/pdf")},
        )

    assert second_resp.status_code == 201
