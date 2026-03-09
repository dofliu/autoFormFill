import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.entity import EntityCreate, EntityResponse, EntityUpdate
from app.schemas.error import ERR_NOT_FOUND
from app.services import entity_relation_service, entity_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users/{user_id}/entities", tags=["Entities"])


def _entity_response(entity) -> dict:
    """Convert Entity ORM instance to dict matching EntityResponse."""
    return entity.to_dict()


@router.post("/", response_model=EntityResponse, status_code=201)
async def create_entity(
    user_id: int, data: EntityCreate, db: AsyncSession = Depends(get_db)
):
    entity = await entity_service.create_entity(db, user_id, data)
    return _entity_response(entity)


@router.get("/", response_model=list[EntityResponse])
async def list_entities(
    user_id: int,
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    entities = await entity_service.list_entities(db, user_id, entity_type)
    return [_entity_response(e) for e in entities]


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    user_id: int, entity_id: int, db: AsyncSession = Depends(get_db)
):
    entity = await entity_service.get_entity(db, entity_id)
    if not entity or entity.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Entity {entity_id} not found", "code": ERR_NOT_FOUND},
        )
    return _entity_response(entity)


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    user_id: int,
    entity_id: int,
    data: EntityUpdate,
    db: AsyncSession = Depends(get_db),
):
    entity = await entity_service.get_entity(db, entity_id)
    if not entity or entity.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Entity {entity_id} not found", "code": ERR_NOT_FOUND},
        )
    updated = await entity_service.update_entity(db, entity_id, data)
    return _entity_response(updated)


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    user_id: int, entity_id: int, db: AsyncSession = Depends(get_db)
):
    entity = await entity_service.get_entity(db, entity_id)
    if not entity or entity.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Entity {entity_id} not found", "code": ERR_NOT_FOUND},
        )
    # Cascade: remove all relations involving this entity
    await entity_relation_service.delete_relations_for_entity(db, entity_id)
    await entity_service.delete_entity(db, entity_id)
