from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.group import GroupCreate, GroupResponse, GroupUpdate
from app.services.group_service import GroupService

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    session: AsyncSession = Depends(get_session),
) -> GroupResponse:
    service = GroupService(session)
    group = await service.create(data)
    return GroupResponse.model_validate(group)


@router.get("/", response_model=list[GroupResponse])
async def list_groups(
    session: AsyncSession = Depends(get_session),
) -> list[GroupResponse]:
    service = GroupService(session)
    groups = await service.get_all()
    return [GroupResponse.model_validate(g) for g in groups]


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    data: GroupUpdate,
    session: AsyncSession = Depends(get_session),
) -> GroupResponse:
    service = GroupService(session)
    group = await service.update(group_id, data)
    return GroupResponse.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = GroupService(session)
    await service.delete(group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
