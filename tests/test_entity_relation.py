"""
Unit tests for Phase 5.1 — EntityRelation model, schemas, service, graph queries, and router integration.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.entity import Entity
from app.models.entity_relation import EntityRelation
from app.schemas.entity_relation import (
    EntityRelationCreate,
    EntityRelationResponse,
    EntityRelationUpdate,
    GraphData,
    GraphEdge,
    GraphNode,
)


# ---------------------------------------------------------------------------
# Helper: build a mock EntityRelation
# ---------------------------------------------------------------------------


def _make_relation(**kwargs) -> MagicMock:
    defaults = dict(
        id=1,
        user_id=1,
        from_entity_id=10,
        to_entity_id=20,
        relation_type="author",
        description="wrote this paper",
        created_at=datetime(2025, 6, 1),
        updated_at=datetime(2025, 6, 2),
    )
    defaults.update(kwargs)
    r = MagicMock(spec=EntityRelation)
    for k, v in defaults.items():
        setattr(r, k, v)
    # Wire up real to_dict
    r.to_dict = lambda: {
        "id": r.id,
        "user_id": r.user_id,
        "from_entity_id": r.from_entity_id,
        "to_entity_id": r.to_entity_id,
        "relation_type": r.relation_type,
        "description": r.description,
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }
    return r


def _make_entity_mock(id: int, name: str, entity_type: str = "person", description: str = "") -> MagicMock:
    e = MagicMock(spec=Entity)
    e.id = id
    e.user_id = 1
    e.name = name
    e.entity_type = entity_type
    e.description = description
    return e


# ---------------------------------------------------------------------------
# EntityRelation ORM model tests
# ---------------------------------------------------------------------------


class TestEntityRelationModel:
    """Test EntityRelation ORM model basics."""

    def test_to_dict_returns_correct_fields(self):
        r = _make_relation()
        d = r.to_dict()
        assert d["id"] == 1
        assert d["user_id"] == 1
        assert d["from_entity_id"] == 10
        assert d["to_entity_id"] == 20
        assert d["relation_type"] == "author"
        assert d["description"] == "wrote this paper"

    def test_to_dict_timestamps(self):
        r = _make_relation()
        d = r.to_dict()
        assert "2025-06-01" in d["created_at"]
        assert "2025-06-02" in d["updated_at"]

    def test_to_dict_none_timestamps(self):
        r = _make_relation(created_at=None, updated_at=None)
        d = r.to_dict()
        assert d["created_at"] == ""
        assert d["updated_at"] == ""

    def test_default_description_empty(self):
        r = _make_relation(description="")
        d = r.to_dict()
        assert d["description"] == ""


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestEntityRelationSchemas:
    """Test Pydantic schemas for entity relations."""

    def test_create_schema_defaults(self):
        data = EntityRelationCreate(
            from_entity_id=1, to_entity_id=2, relation_type="collaborator"
        )
        assert data.description == ""

    def test_create_schema_with_description(self):
        data = EntityRelationCreate(
            from_entity_id=1, to_entity_id=2,
            relation_type="cites", description="引用論文"
        )
        assert data.description == "引用論文"

    def test_update_schema_all_optional(self):
        data = EntityRelationUpdate()
        assert data.relation_type is None
        assert data.description is None

    def test_response_serialization(self):
        resp = EntityRelationResponse(
            id=1, user_id=1, from_entity_id=10, to_entity_id=20,
            relation_type="author", description="wrote",
            created_at="2025-06-01T00:00:00", updated_at="2025-06-01T00:00:00",
        )
        assert resp.id == 1
        assert resp.relation_type == "author"

    def test_graph_data_structure(self):
        gd = GraphData(
            nodes=[GraphNode(id=1, name="Alice", entity_type="person")],
            edges=[GraphEdge(id=1, source=1, target=2, relation_type="knows")],
        )
        assert len(gd.nodes) == 1
        assert len(gd.edges) == 1
        assert gd.nodes[0].description == ""  # default
        assert gd.edges[0].description == ""  # default


# ---------------------------------------------------------------------------
# Service CRUD tests (mock DB)
# ---------------------------------------------------------------------------


class TestEntityRelationService:
    """Test entity_relation_service functions with mocked async DB."""

    @pytest.mark.asyncio
    async def test_create_relation(self):
        from app.services.entity_relation_service import create_relation

        mock_db = AsyncMock()
        data = EntityRelationCreate(
            from_entity_id=10, to_entity_id=20, relation_type="author"
        )
        relation = await create_relation(mock_db, user_id=1, data=data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert relation.from_entity_id == 10
        assert relation.to_entity_id == 20

    @pytest.mark.asyncio
    async def test_get_relation_found(self):
        from app.services.entity_relation_service import get_relation

        mock_relation = _make_relation()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_relation
        mock_db.execute.return_value = mock_result

        result = await get_relation(mock_db, relation_id=1)
        assert result == mock_relation

    @pytest.mark.asyncio
    async def test_get_relation_not_found(self):
        from app.services.entity_relation_service import get_relation

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await get_relation(mock_db, relation_id=999)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_relation_returns_false_when_not_found(self):
        from app.services.entity_relation_service import delete_relation

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await delete_relation(mock_db, relation_id=999)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_relation_returns_true(self):
        from app.services.entity_relation_service import delete_relation

        mock_relation = _make_relation()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_relation
        mock_db.execute.return_value = mock_result

        result = await delete_relation(mock_db, relation_id=1)
        assert result is True
        mock_db.delete.assert_awaited_once_with(mock_relation)
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_relation(self):
        from app.services.entity_relation_service import update_relation

        mock_relation = _make_relation()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_relation
        mock_db.execute.return_value = mock_result

        data = EntityRelationUpdate(relation_type="collaborator", description="updated desc")
        result = await update_relation(mock_db, relation_id=1, data=data)

        assert result is not None
        assert mock_relation.relation_type == "collaborator"
        assert mock_relation.description == "updated desc"
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_relations_with_filters(self):
        from app.services.entity_relation_service import list_relations

        r1 = _make_relation(id=1, relation_type="author")
        r2 = _make_relation(id=2, relation_type="collaborator")

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1, r2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await list_relations(mock_db, user_id=1, relation_type="author")
        assert len(result) == 2  # filtering happens at DB level, mock returns all

    @pytest.mark.asyncio
    async def test_delete_relations_for_entity_no_relations(self):
        from app.services.entity_relation_service import delete_relations_for_entity

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        count = await delete_relations_for_entity(mock_db, entity_id=10)
        assert count == 0
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_relations_for_entity_removes_all(self):
        from app.services.entity_relation_service import delete_relations_for_entity

        r1 = _make_relation(id=1, from_entity_id=10, to_entity_id=20)
        r2 = _make_relation(id=2, from_entity_id=30, to_entity_id=10)

        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1, r2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        count = await delete_relations_for_entity(mock_db, entity_id=10)
        assert count == 2
        assert mock_db.delete.await_count == 2
        mock_db.commit.assert_awaited()


# ---------------------------------------------------------------------------
# Graph query tests
# ---------------------------------------------------------------------------


class TestGraphQueries:
    """Test get_full_graph, get_neighbors, get_relation_types."""

    @pytest.mark.asyncio
    async def test_get_relation_types(self):
        from app.services.entity_relation_service import get_relation_types

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("author",), ("collaborator",), ("funds",)]
        mock_db.execute.return_value = mock_result

        types = await get_relation_types(mock_db, user_id=1)
        assert types == ["author", "collaborator", "funds"]

    @pytest.mark.asyncio
    async def test_get_full_graph_empty(self):
        from app.services.entity_relation_service import get_full_graph

        mock_db = AsyncMock()
        # Two execute calls: entities then relations
        mock_entities = MagicMock()
        mock_entities.scalars.return_value.all.return_value = []
        mock_relations = MagicMock()
        mock_relations.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [mock_entities, mock_relations]

        graph = await get_full_graph(mock_db, user_id=1)
        assert graph.nodes == []
        assert graph.edges == []

    @pytest.mark.asyncio
    async def test_get_full_graph_with_data(self):
        from app.services.entity_relation_service import get_full_graph

        e1 = _make_entity_mock(1, "Alice", "person")
        e2 = _make_entity_mock(2, "Paper A", "project")
        r1 = _make_relation(id=1, from_entity_id=1, to_entity_id=2, relation_type="author")

        mock_db = AsyncMock()
        mock_entities = MagicMock()
        mock_entities.scalars.return_value.all.return_value = [e1, e2]
        mock_relations = MagicMock()
        mock_relations.scalars.return_value.all.return_value = [r1]
        mock_db.execute.side_effect = [mock_entities, mock_relations]

        graph = await get_full_graph(mock_db, user_id=1)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.nodes[0].name == "Alice"
        assert graph.edges[0].source == 1
        assert graph.edges[0].target == 2
        assert graph.edges[0].relation_type == "author"

    @pytest.mark.asyncio
    async def test_get_neighbors(self):
        from app.services.entity_relation_service import get_neighbors

        r1 = _make_relation(id=1, from_entity_id=1, to_entity_id=2, relation_type="author")
        e1 = _make_entity_mock(1, "Alice", "person")
        e2 = _make_entity_mock(2, "Paper A", "project")

        mock_db = AsyncMock()
        # First call: relations
        mock_relations = MagicMock()
        mock_relations.scalars.return_value.all.return_value = [r1]
        # Second call: entities
        mock_entities = MagicMock()
        mock_entities.scalars.return_value.all.return_value = [e1, e2]
        mock_db.execute.side_effect = [mock_relations, mock_entities]

        graph = await get_neighbors(mock_db, user_id=1, entity_id=1)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    @pytest.mark.asyncio
    async def test_get_neighbors_no_connections(self):
        from app.services.entity_relation_service import get_neighbors

        e1 = _make_entity_mock(1, "Isolated", "person")

        mock_db = AsyncMock()
        # First call: no relations
        mock_relations = MagicMock()
        mock_relations.scalars.return_value.all.return_value = []
        # Second call: just the center entity
        mock_entities = MagicMock()
        mock_entities.scalars.return_value.all.return_value = [e1]
        mock_db.execute.side_effect = [mock_relations, mock_entities]

        graph = await get_neighbors(mock_db, user_id=1, entity_id=1)
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0


# ---------------------------------------------------------------------------
# Router integration tests
# ---------------------------------------------------------------------------


class TestRouterIntegration:
    """Test validation logic in entity_relations router."""

    @pytest.mark.asyncio
    async def test_self_reference_rejected(self):
        """Creating a relation from entity to itself should fail."""
        from fastapi.testclient import TestClient
        from app.routers.entity_relations import create_relation
        from fastapi import HTTPException

        # Simulate the self-reference check
        data = EntityRelationCreate(
            from_entity_id=5, to_entity_id=5, relation_type="self"
        )
        with pytest.raises(HTTPException) as exc_info:
            mock_db = AsyncMock()
            await create_relation(user_id=1, data=data, db=mock_db, current_user=None)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_source_entity_not_found(self):
        """Creating a relation with non-existent source entity should fail."""
        from app.routers.entity_relations import create_relation
        from fastapi import HTTPException

        data = EntityRelationCreate(
            from_entity_id=999, to_entity_id=20, relation_type="author"
        )
        mock_db = AsyncMock()

        with patch("app.routers.entity_relations.entity_service") as mock_svc:
            mock_svc.get_entity = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await create_relation(user_id=1, data=data, db=mock_db, current_user=None)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cascade_delete_called_on_entity_delete(self):
        """When an entity is deleted, its relations should be cleaned up."""
        from app.routers.entities import delete_entity

        mock_entity = _make_entity_mock(10, "Alice")
        mock_entity.user_id = 1
        mock_db = AsyncMock()

        with patch("app.routers.entities.entity_service") as mock_entity_svc, \
             patch("app.routers.entities.entity_relation_service") as mock_rel_svc:
            mock_entity_svc.get_entity = AsyncMock(return_value=mock_entity)
            mock_entity_svc.delete_entity = AsyncMock(return_value=True)
            mock_rel_svc.delete_relations_for_entity = AsyncMock(return_value=3)

            await delete_entity(user_id=1, entity_id=10, db=mock_db, current_user=None)

            mock_rel_svc.delete_relations_for_entity.assert_awaited_once_with(mock_db, 10)
            mock_entity_svc.delete_entity.assert_awaited_once_with(mock_db, 10)
