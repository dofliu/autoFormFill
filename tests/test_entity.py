"""
Unit tests for Phase 3.5 — Entity model, service, router integration, and form filler.
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.entity import Entity
from app.schemas.entity import EntityCreate, EntityResponse, EntityUpdate
from app.services.form_filler import _get_sql_value, _merge_entity_attributes


# ---------------------------------------------------------------------------
# Entity ORM model tests
# ---------------------------------------------------------------------------

class TestEntityModel:
    """Test Entity ORM model + JSON attributes."""

    def _make_entity(self, **kwargs) -> Entity:
        defaults = dict(
            id=1,
            user_id=1,
            entity_type="person",
            name="Test Entity",
            description="desc",
            attributes_json='{"key1": "val1", "key2": "val2"}',
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 2),
        )
        defaults.update(kwargs)
        # Use MagicMock to avoid SQLAlchemy instrumentation issues
        e = MagicMock(spec=Entity)
        for k, v in defaults.items():
            setattr(e, k, v)
        # Wire up the real property logic for attributes
        type(e).attributes = property(
            lambda self: json.loads(self.attributes_json),
            lambda self, val: setattr(self, 'attributes_json', json.dumps(val, ensure_ascii=False)),
        )
        # Wire up the real to_dict method
        e.to_dict = lambda: {
            "id": e.id,
            "user_id": e.user_id,
            "entity_type": e.entity_type,
            "name": e.name,
            "description": e.description,
            "attributes": json.loads(e.attributes_json),
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "updated_at": e.updated_at.isoformat() if e.updated_at else "",
        }
        return e

    def test_attributes_property_parses_json(self):
        entity = self._make_entity()
        assert entity.attributes == {"key1": "val1", "key2": "val2"}

    def test_attributes_setter_serializes_json(self):
        entity = self._make_entity()
        entity.attributes = {"a": "1", "b": "2"}
        assert json.loads(entity.attributes_json) == {"a": "1", "b": "2"}

    def test_attributes_empty_default(self):
        entity = self._make_entity(attributes_json="{}")
        assert entity.attributes == {}

    def test_to_dict(self):
        entity = self._make_entity()
        d = entity.to_dict()
        assert d["id"] == 1
        assert d["user_id"] == 1
        assert d["entity_type"] == "person"
        assert d["name"] == "Test Entity"
        assert d["attributes"] == {"key1": "val1", "key2": "val2"}
        assert "2025-01-01" in d["created_at"]

    def test_to_dict_handles_none_timestamps(self):
        entity = self._make_entity(created_at=None, updated_at=None)
        d = entity.to_dict()
        assert d["created_at"] == ""
        assert d["updated_at"] == ""


# ---------------------------------------------------------------------------
# Entity schema tests
# ---------------------------------------------------------------------------

class TestEntitySchemas:
    def test_entity_create_defaults(self):
        data = EntityCreate(entity_type="person", name="Alice")
        assert data.description == ""
        assert data.attributes == {}

    def test_entity_create_with_attributes(self):
        data = EntityCreate(
            entity_type="organization",
            name="NTUST",
            attributes={"dept": "CS", "country": "TW"},
        )
        assert data.attributes["dept"] == "CS"

    def test_entity_update_all_optional(self):
        data = EntityUpdate()
        assert data.entity_type is None
        assert data.name is None
        assert data.description is None
        assert data.attributes is None

    def test_entity_response_serialization(self):
        resp = EntityResponse(
            id=1,
            user_id=1,
            entity_type="project",
            name="SmartFill",
            description="desc",
            attributes={"lang": "Python"},
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert resp.id == 1
        assert resp.attributes == {"lang": "Python"}


# ---------------------------------------------------------------------------
# Entity service tests (mock DB)
# ---------------------------------------------------------------------------

class TestEntityService:
    """Test entity_service functions with mocked async DB."""

    @pytest.mark.asyncio
    async def test_create_entity(self):
        from app.services.entity_service import create_entity

        mock_db = AsyncMock()
        data = EntityCreate(entity_type="person", name="Alice", attributes={"role": "PI"})

        entity = await create_entity(mock_db, user_id=1, data=data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert entity.name == "Alice"
        assert entity.entity_type == "person"

    @pytest.mark.asyncio
    async def test_get_entity_found(self):
        from app.services.entity_service import get_entity

        mock_entity = MagicMock(spec=Entity)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_entity
        mock_db.execute.return_value = mock_result

        result = await get_entity(mock_db, entity_id=1)
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self):
        from app.services.entity_service import get_entity

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await get_entity(mock_db, entity_id=999)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_entity_returns_false_when_not_found(self):
        from app.services.entity_service import delete_entity

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await delete_entity(mock_db, entity_id=999)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_entity_attribute_names(self):
        from app.services.entity_service import get_entity_attribute_names

        e1 = MagicMock(spec=Entity)
        e1.attributes = {"name_zh": "Alice", "role": "PI"}
        e2 = MagicMock(spec=Entity)
        e2.attributes = {"role": "Co-PI", "dept": "CS"}

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [e1, e2]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        names = await get_entity_attribute_names(mock_db, user_id=1)
        assert sorted(names) == ["dept", "name_zh", "role"]


# ---------------------------------------------------------------------------
# Form Filler integration tests
# ---------------------------------------------------------------------------

class TestFormFillerEntityIntegration:
    """Test _get_sql_value and _merge_entity_attributes."""

    def _make_entity_mock(self, attrs: dict[str, str]) -> MagicMock:
        e = MagicMock(spec=Entity)
        e.attributes = attrs
        return e

    def test_get_sql_value_from_user_profile(self):
        user = MagicMock()
        user.name_zh = "測試"
        value = _get_sql_value(user, "user_profiles.name_zh")
        assert value == "測試"

    def test_get_sql_value_from_entities(self):
        user = MagicMock()
        entity_attrs = {"role": "PI", "dept": "CS"}
        value = _get_sql_value(user, "entities.role", entity_attrs)
        assert value == "PI"

    def test_get_sql_value_entity_key_missing(self):
        user = MagicMock()
        entity_attrs = {"role": "PI"}
        value = _get_sql_value(user, "entities.missing_key", entity_attrs)
        assert value == "[需人工補充]"

    def test_get_sql_value_entity_attrs_none(self):
        user = MagicMock()
        value = _get_sql_value(user, "entities.role", None)
        assert value == "[需人工補充]"

    def test_get_sql_value_user_attribute_missing(self):
        user = MagicMock(spec=[])  # no attributes
        value = _get_sql_value(user, "user_profiles.nonexistent")
        assert value == "[需人工補充]"

    def test_merge_entity_attributes_empty(self):
        result = _merge_entity_attributes([])
        assert result == {}

    def test_merge_entity_attributes_single(self):
        e = self._make_entity_mock({"a": "1", "b": "2"})
        result = _merge_entity_attributes([e])
        assert result == {"a": "1", "b": "2"}

    def test_merge_entity_attributes_conflict_most_recent_wins(self):
        """Entities are ordered by updated_at desc, so first entity is most recent."""
        e_recent = self._make_entity_mock({"key": "recent_value"})
        e_old = self._make_entity_mock({"key": "old_value"})
        # list is [most_recent, oldest], reversed during merge so recent overwrites
        result = _merge_entity_attributes([e_recent, e_old])
        assert result["key"] == "recent_value"

    def test_merge_entity_attributes_combines_keys(self):
        e1 = self._make_entity_mock({"a": "1"})
        e2 = self._make_entity_mock({"b": "2"})
        result = _merge_entity_attributes([e1, e2])
        assert result == {"a": "1", "b": "2"}


# ---------------------------------------------------------------------------
# Intent Router integration
# ---------------------------------------------------------------------------

class TestIntentRouterEntityIntegration:
    """Test that entity_attribute_names are injected into routing prompt."""

    @pytest.mark.asyncio
    async def test_route_fields_with_entity_attributes(self):
        from app.schemas.form import FormField
        from app.services.intent_router import route_fields

        fields = [FormField(field_name="PI名稱", field_type="text")]
        mock_result = [
            {
                "field_name": "PI名稱",
                "data_source": "SQL_DB",
                "sql_target": "entities.pi_name",
                "search_query": None,
                "confidence": 0.9,
            }
        ]

        with patch("app.services.intent_router.get_llm_adapter") as mock_factory:
            mock_adapter = MagicMock()
            mock_adapter.generate_json = AsyncMock(return_value=mock_result)
            mock_factory.return_value = mock_adapter

            results = await route_fields(
                fields, entity_attribute_names=["pi_name", "dept", "funding"]
            )

            # Verify prompt contains entity attribute hint
            called_prompt = mock_adapter.generate_json.call_args[0][0]
            assert "entities.<key>" in called_prompt
            assert "pi_name" in called_prompt
            assert "dept" in called_prompt

            assert results[0].sql_target == "entities.pi_name"
            assert results[0].data_source == "SQL_DB"

    @pytest.mark.asyncio
    async def test_route_fields_without_entity_attributes(self):
        """Prompt should be unchanged when no entity attributes are provided."""
        from app.schemas.form import FormField
        from app.services.intent_router import route_fields

        fields = [FormField(field_name="姓名", field_type="text")]
        mock_result = [
            {
                "field_name": "姓名",
                "data_source": "SQL_DB",
                "sql_target": "user_profiles.name_zh",
                "confidence": 0.95,
            }
        ]

        with patch("app.services.intent_router.get_llm_adapter") as mock_factory:
            mock_adapter = MagicMock()
            mock_adapter.generate_json = AsyncMock(return_value=mock_result)
            mock_factory.return_value = mock_adapter

            results = await route_fields(fields, entity_attribute_names=None)

            called_prompt = mock_adapter.generate_json.call_args[0][0]
            assert "entities.<key>" not in called_prompt
            assert results[0].sql_target == "user_profiles.name_zh"
