"""EntityRelation async CRUD + graph query helpers."""

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.entity_relation import EntityRelation
from app.schemas.entity_relation import (
    EntityRelationCreate,
    EntityRelationUpdate,
    GraphData,
    GraphEdge,
    GraphNode,
)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_relation(
    db: AsyncSession, user_id: int, data: EntityRelationCreate
) -> EntityRelation:
    """Create a new directed relation between two entities."""
    relation = EntityRelation(
        user_id=user_id,
        from_entity_id=data.from_entity_id,
        to_entity_id=data.to_entity_id,
        relation_type=data.relation_type,
        description=data.description,
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return relation


async def get_relation(db: AsyncSession, relation_id: int) -> EntityRelation | None:
    """Fetch a single relation by ID."""
    result = await db.execute(
        select(EntityRelation).where(EntityRelation.id == relation_id)
    )
    return result.scalar_one_or_none()


async def list_relations(
    db: AsyncSession,
    user_id: int,
    relation_type: str | None = None,
    entity_id: int | None = None,
) -> list[EntityRelation]:
    """List relations for a user, optionally filtered by type or entity."""
    stmt = select(EntityRelation).where(EntityRelation.user_id == user_id)
    if relation_type:
        stmt = stmt.where(EntityRelation.relation_type == relation_type)
    if entity_id is not None:
        stmt = stmt.where(
            or_(
                EntityRelation.from_entity_id == entity_id,
                EntityRelation.to_entity_id == entity_id,
            )
        )
    stmt = stmt.order_by(EntityRelation.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_relation(
    db: AsyncSession, relation_id: int, data: EntityRelationUpdate
) -> EntityRelation | None:
    """Update an existing relation. Only provided fields are changed."""
    relation = await get_relation(db, relation_id)
    if not relation:
        return None
    if data.relation_type is not None:
        relation.relation_type = data.relation_type
    if data.description is not None:
        relation.description = data.description
    await db.commit()
    await db.refresh(relation)
    return relation


async def delete_relation(db: AsyncSession, relation_id: int) -> bool:
    """Delete a relation. Returns True if deleted, False if not found."""
    relation = await get_relation(db, relation_id)
    if not relation:
        return False
    await db.delete(relation)
    await db.commit()
    return True


async def delete_relations_for_entity(db: AsyncSession, entity_id: int) -> int:
    """Delete all relations where entity_id is either source or target.

    Called when an Entity is deleted to avoid dangling references.
    Returns the number of relations removed.
    """
    stmt = select(EntityRelation).where(
        or_(
            EntityRelation.from_entity_id == entity_id,
            EntityRelation.to_entity_id == entity_id,
        )
    )
    result = await db.execute(stmt)
    relations = list(result.scalars().all())
    for r in relations:
        await db.delete(r)
    if relations:
        await db.commit()
    return len(relations)


# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------


async def get_relation_types(db: AsyncSession, user_id: int) -> list[str]:
    """Return distinct relation types for a user."""
    stmt = (
        select(EntityRelation.relation_type)
        .where(EntityRelation.user_id == user_id)
        .distinct()
        .order_by(EntityRelation.relation_type)
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def get_full_graph(db: AsyncSession, user_id: int) -> GraphData:
    """Build a complete graph of all entities + relations for a user."""
    # Fetch all entities
    entity_result = await db.execute(
        select(Entity).where(Entity.user_id == user_id).order_by(Entity.id)
    )
    entities = list(entity_result.scalars().all())

    # Fetch all relations
    relation_result = await db.execute(
        select(EntityRelation)
        .where(EntityRelation.user_id == user_id)
        .order_by(EntityRelation.id)
    )
    relations = list(relation_result.scalars().all())

    nodes = [
        GraphNode(
            id=e.id,
            name=e.name,
            entity_type=e.entity_type,
            description=e.description,
        )
        for e in entities
    ]
    edges = [
        GraphEdge(
            id=r.id,
            source=r.from_entity_id,
            target=r.to_entity_id,
            relation_type=r.relation_type,
            description=r.description,
        )
        for r in relations
    ]
    return GraphData(nodes=nodes, edges=edges)


async def get_neighbors(
    db: AsyncSession, user_id: int, entity_id: int
) -> GraphData:
    """Build a 1-hop subgraph around a given entity.

    Returns the center entity, all directly connected entities,
    and the relations between them.
    """
    # Get all relations involving this entity
    relation_result = await db.execute(
        select(EntityRelation).where(
            EntityRelation.user_id == user_id,
            or_(
                EntityRelation.from_entity_id == entity_id,
                EntityRelation.to_entity_id == entity_id,
            ),
        )
    )
    relations = list(relation_result.scalars().all())

    # Collect all entity IDs needed (center + neighbors)
    entity_ids: set[int] = {entity_id}
    for r in relations:
        entity_ids.add(r.from_entity_id)
        entity_ids.add(r.to_entity_id)

    # Fetch those entities
    if entity_ids:
        entity_result = await db.execute(
            select(Entity).where(
                Entity.id.in_(entity_ids),
                Entity.user_id == user_id,
            )
        )
        entities = list(entity_result.scalars().all())
    else:
        entities = []

    nodes = [
        GraphNode(
            id=e.id,
            name=e.name,
            entity_type=e.entity_type,
            description=e.description,
        )
        for e in entities
    ]
    edges = [
        GraphEdge(
            id=r.id,
            source=r.from_entity_id,
            target=r.to_entity_id,
            relation_type=r.relation_type,
            description=r.description,
        )
        for r in relations
    ]
    return GraphData(nodes=nodes, edges=edges)
