"""Entity async CRUD operations + attribute name aggregation."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.schemas.entity import EntityCreate, EntityUpdate


async def create_entity(db: AsyncSession, user_id: int, data: EntityCreate) -> Entity:
    """Create a new entity under the given user."""
    entity = Entity(
        user_id=user_id,
        entity_type=data.entity_type,
        name=data.name,
        description=data.description,
        attributes_json=json.dumps(data.attributes, ensure_ascii=False),
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def get_entity(db: AsyncSession, entity_id: int) -> Entity | None:
    """Fetch a single entity by ID."""
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    return result.scalar_one_or_none()


async def list_entities(
    db: AsyncSession,
    user_id: int,
    entity_type: str | None = None,
) -> list[Entity]:
    """List all entities for a user, optionally filtered by type."""
    stmt = select(Entity).where(Entity.user_id == user_id)
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    stmt = stmt.order_by(Entity.updated_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_entity(
    db: AsyncSession, entity_id: int, data: EntityUpdate
) -> Entity | None:
    """Update an existing entity. Only provided fields are changed."""
    entity = await get_entity(db, entity_id)
    if not entity:
        return None
    if data.entity_type is not None:
        entity.entity_type = data.entity_type
    if data.name is not None:
        entity.name = data.name
    if data.description is not None:
        entity.description = data.description
    if data.attributes is not None:
        entity.attributes = data.attributes
    await db.commit()
    await db.refresh(entity)
    return entity


async def delete_entity(db: AsyncSession, entity_id: int) -> bool:
    """Delete an entity. Returns True if deleted, False if not found."""
    entity = await get_entity(db, entity_id)
    if not entity:
        return False
    await db.delete(entity)
    await db.commit()
    return True


async def get_entity_attribute_names(db: AsyncSession, user_id: int) -> list[str]:
    """Collect all unique attribute keys across a user's entities.

    Used by Intent Router to build the list of available entity fields
    for the routing prompt.
    """
    entities = await list_entities(db, user_id)
    keys: set[str] = set()
    for entity in entities:
        keys.update(entity.attributes.keys())
    return sorted(keys)
