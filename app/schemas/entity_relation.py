"""Pydantic schemas for EntityRelation CRUD + graph query responses."""

from pydantic import BaseModel


class EntityRelationCreate(BaseModel):
    from_entity_id: int
    to_entity_id: int
    relation_type: str
    description: str = ""


class EntityRelationUpdate(BaseModel):
    relation_type: str | None = None
    description: str | None = None


class EntityRelationResponse(BaseModel):
    id: int
    user_id: int
    from_entity_id: int
    to_entity_id: int
    relation_type: str
    description: str
    created_at: str
    updated_at: str


# --- Graph query response schemas ---


class GraphNode(BaseModel):
    """A node in the graph, corresponding to an Entity."""
    id: int
    name: str
    entity_type: str
    description: str = ""


class GraphEdge(BaseModel):
    """A directed edge in the graph (source/target for D3 compatibility)."""
    id: int
    source: int
    target: int
    relation_type: str
    description: str = ""


class GraphData(BaseModel):
    """Full graph data suitable for frontend visualization."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
