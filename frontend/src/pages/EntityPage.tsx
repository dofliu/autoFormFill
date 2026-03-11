import { useEffect, useState } from "react";
import * as entitiesApi from "../api/entities";
import { useAuth } from "../contexts/AuthContext";
import type { Entity, EntityCreate } from "../types/entity";

const ENTITY_TYPES = ["person", "organization", "project"];

export default function EntityPage() {
  const { user } = useAuth();
  const userId = user?.id ?? 1;

  const [entities, setEntities] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [editing, setEditing] = useState(false);
  const [filterType, setFilterType] = useState("");
  const [saving, setSaving] = useState(false);

  // Form state
  const [form, setForm] = useState<EntityCreate>({
    entity_type: "person",
    name: "",
    description: "",
    attributes: {},
  });

  // Dynamic attributes editing
  const [attrKey, setAttrKey] = useState("");
  const [attrValue, setAttrValue] = useState("");

  const loadEntities = () => {
    entitiesApi
      .listEntities(userId, filterType || undefined)
      .then(setEntities);
  };

  useEffect(() => {
    loadEntities();
  }, [userId, filterType]);

  const handleSelect = (e: Entity) => {
    setSelected(e);
    setEditing(false);
  };

  const startCreate = () => {
    setForm({ entity_type: "person", name: "", description: "", attributes: {} });
    setEditing(true);
    setSelected(null);
  };

  const startEdit = () => {
    if (!selected) return;
    setForm({
      entity_type: selected.entity_type,
      name: selected.name,
      description: selected.description,
      attributes: { ...selected.attributes },
    });
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (selected) {
        const updated = await entitiesApi.updateEntity(userId, selected.id, form);
        setEntities((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
        setSelected(updated);
      } else {
        const created = await entitiesApi.createEntity(userId, form);
        setEntities((prev) => [...prev, created]);
        setSelected(created);
      }
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    await entitiesApi.deleteEntity(userId, selected.id);
    setEntities((prev) => prev.filter((e) => e.id !== selected.id));
    setSelected(null);
  };

  const addAttribute = () => {
    if (!attrKey.trim()) return;
    setForm({
      ...form,
      attributes: { ...(form.attributes || {}), [attrKey.trim()]: attrValue },
    });
    setAttrKey("");
    setAttrValue("");
  };

  const removeAttribute = (key: string) => {
    const next = { ...(form.attributes || {}) };
    delete next[key];
    setForm({ ...form, attributes: next });
  };

  const typeLabel = (t: string) => {
    switch (t) {
      case "person": return "人員";
      case "organization": return "組織";
      case "project": return "專案";
      default: return t;
    }
  };

  const typeBadgeClass = (t: string) => {
    switch (t) {
      case "person": return "bg-blue-100 text-blue-700";
      case "organization": return "bg-green-100 text-green-700";
      case "project": return "bg-purple-100 text-purple-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="flex h-full">
      {/* Left: Entity List */}
      <div className="w-64 border-r border-gray-200 p-4 flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">實體管理</h2>
        <button
          onClick={startCreate}
          className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新增實體
        </button>
        <a
          href="/graph"
          className="block w-full py-2 text-center border border-gray-300 text-sm rounded-lg hover:bg-gray-50 transition-colors text-gray-600"
        >
          🕸️ 查看圖譜
        </a>

        {/* Type filter */}
        <select
          className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm mt-1"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">全部類型</option>
          {ENTITY_TYPES.map((t) => (
            <option key={t} value={t}>{typeLabel(t)}</option>
          ))}
        </select>

        <div className="flex flex-col gap-1 mt-2 overflow-y-auto">
          {entities.map((e) => (
            <button
              key={e.id}
              onClick={() => handleSelect(e)}
              className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selected?.id === e.id
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span className={`inline-block px-1.5 py-0.5 text-xs rounded mr-1.5 ${typeBadgeClass(e.entity_type)}`}>
                {typeLabel(e.entity_type)}
              </span>
              {e.name}
            </button>
          ))}
          {entities.length === 0 && (
            <p className="text-sm text-gray-400 mt-2">尚無實體</p>
          )}
        </div>
      </div>

      {/* Right: Detail / Edit */}
      <div className="flex-1 p-6 overflow-y-auto">
        {editing ? (
          <div className="max-w-lg">
            <h2 className="text-lg font-semibold mb-4">
              {selected ? "編輯實體" : "新增實體"}
            </h2>
            <div className="grid gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">類型</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  value={form.entity_type}
                  onChange={(e) => setForm({ ...form, entity_type: e.target.value })}
                >
                  {ENTITY_TYPES.map((t) => (
                    <option key={t} value={t}>{typeLabel(t)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">名稱</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y"
                  rows={3}
                  value={form.description || ""}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>

              {/* Dynamic Attributes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">屬性</label>
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                  {Object.entries(form.attributes || {}).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium text-gray-600 w-28 truncate">{k}</span>
                      <input
                        className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                        value={v}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            attributes: { ...(form.attributes || {}), [k]: e.target.value },
                          })
                        }
                      />
                      <button
                        onClick={() => removeAttribute(k)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        移除
                      </button>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      className="w-28 border border-gray-300 rounded px-2 py-1 text-sm"
                      placeholder="屬性名"
                      value={attrKey}
                      onChange={(e) => setAttrKey(e.target.value)}
                    />
                    <input
                      className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                      placeholder="屬性值"
                      value={attrValue}
                      onChange={(e) => setAttrValue(e.target.value)}
                    />
                    <button
                      onClick={addAttribute}
                      className="px-2 py-1 text-xs bg-gray-200 rounded hover:bg-gray-300"
                    >
                      加入
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "儲存中..." : "儲存"}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
            </div>
          </div>
        ) : selected ? (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className={`inline-block px-2 py-1 text-xs rounded ${typeBadgeClass(selected.entity_type)}`}>
                {typeLabel(selected.entity_type)}
              </span>
              <h2 className="text-lg font-semibold">{selected.name}</h2>
              <button
                onClick={startEdit}
                className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                編輯
              </button>
              <button
                onClick={handleDelete}
                className="px-3 py-1 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
              >
                刪除
              </button>
            </div>

            {selected.description && (
              <p className="text-sm text-gray-600 mb-4">{selected.description}</p>
            )}

            <h3 className="text-sm font-semibold text-gray-700 mb-2">屬性</h3>
            {Object.keys(selected.attributes).length === 0 ? (
              <p className="text-sm text-gray-400">尚無自訂屬性</p>
            ) : (
              <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm max-w-lg">
                {Object.entries(selected.attributes).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-gray-500">{k}</span>
                    <p className="font-medium text-gray-800">{v || "—"}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 text-xs text-gray-400">
              建立時間：{selected.created_at} | 更新時間：{selected.updated_at}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            請從左側選擇或新增實體
          </div>
        )}
      </div>
    </div>
  );
}
