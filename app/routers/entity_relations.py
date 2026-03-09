"""Entity Relations API — CRUD + graph query endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.entity_relation import (
    EntityRelationCreate,
    EntityRelationResponse,
    EntityRelationUpdate,
    GraphData,
)
from app.schemas.error import ERR_NOT_FOUND, ERR_VALIDATION
from app.services import entity_relation_service, entity_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users/{user_id}/entity-relations",
    tags=["Entity Relations"],
)


def _relation_response(relation) -> dict:
    """Convert EntityRelation ORM instance to dict matching EntityRelationResponse."""
    return relation.to_dict()


# --- Static path routes FIRST (before /{relation_id}) ---


@router.get("/types", response_model=list[str])
async def get_relation_types(
    user_id: int, db: AsyncSession = Depends(get_db)
):
    """Return distinct relation types for a user."""
    return await entity_relation_service.get_relation_types(db, user_id)


@router.get("/graph", response_model=GraphData)
async def get_full_graph(
    user_id: int, db: AsyncSession = Depends(get_db)
):
    """Return full graph data (all entities + relations) for visualization."""
    return await entity_relation_service.get_full_graph(db, user_id)


@router.get("/graph/{entity_id}", response_model=GraphData)
async def get_neighbor_graph(
    user_id: int, entity_id: int, db: AsyncSession = Depends(get_db)
):
    """Return 1-hop subgraph around a specific entity."""
    return await entity_relation_service.get_neighbors(db, user_id, entity_id)


# --- CRUD routes ---


@router.post("/", response_model=EntityRelationResponse, status_code=201)
async def create_relation(
    user_id: int,
    data: EntityRelationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a directed relation between two entities."""
    # Validate: no self-reference
    if data.from_entity_id == data.to_entity_id:
        raise HTTPException(
            status_code=400,
            detail={"detail": "Cannot create a relation from an entity to itself", "code": ERR_VALIDATION},
        )

    # Validate: both entities exist and belong to this user
    from_entity = await entity_service.get_entity(db, data.from_entity_id)
    if not from_entity or from_entity.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Source entity {data.from_entity_id} not found", "code": ERR_NOT_FOUND},
        )
    to_entity = await entity_service.get_entity(db, data.to_entity_id)
    if not to_entity or to_entity.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Target entity {data.to_entity_id} not found", "code": ERR_NOT_FOUND},
        )

    relation = await entity_relation_service.create_relation(db, user_id, data)
    return _relation_response(relation)


@router.get("/", response_model=list[EntityRelationResponse])
async def list_relations(
    user_id: int,
    relation_type: str | None = None,
    entity_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List relations, optionally filtered by type or entity involvement."""
    relations = await entity_relation_service.list_relations(
        db, user_id, relation_type, entity_id
    )
    return [_relation_response(r) for r in relations]


@router.get("/{relation_id}", response_model=EntityRelationResponse)
async def get_relation(
    user_id: int, relation_id: int, db: AsyncSession = Depends(get_db)
):
    """Get a single relation by ID."""
    relation = await entity_relation_service.get_relation(db, relation_id)
    if not relation or relation.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Relation {relation_id} not found", "code": ERR_NOT_FOUND},
        )
    return _relation_response(relation)


@router.put("/{relation_id}", response_model=EntityRelationResponse)
async def update_relation(
    user_id: int,
    relation_id: int,
    data: EntityRelationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a relation (type / description only — endpoints not changeable)."""
    relation = await entity_relation_service.get_relation(db, relation_id)
    if not relation or relation.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Relation {relation_id} not found", "code": ERR_NOT_FOUND},
        )
    updated = await entity_relation_service.update_relation(db, relation_id, data)
    return _relation_response(updated)


@router.delete("/{relation_id}", status_code=204)
async def delete_relation(
    user_id: int, relation_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a relation."""
    relation = await entity_relation_service.get_relation(db, relation_id)
    if not relation or relation.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Relation {relation_id} not found", "code": ERR_NOT_FOUND},
        )
    await entity_relation_service.delete_relation(db, relation_id)
