import { useEffect, useState } from "react";
import type { Entity } from "../types/entity";
import type { EntityRelationCreate } from "../types/entityRelation";

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (data: EntityRelationCreate) => Promise<void>;
  entities: Entity[];
  sourceEntityId?: number;
  existingTypes: string[];
}

export default function AddRelationModal({
  open,
  onClose,
  onSave,
  entities,
  sourceEntityId,
  existingTypes,
}: Props) {
  const [fromId, setFromId] = useState<number | "">(sourceEntityId ?? "");
  const [toId, setToId] = useState<number | "">("");
  const [relationType, setRelationType] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setFromId(sourceEntityId ?? "");
      setToId("");
      setRelationType("");
      setDescription("");
      setError("");
    }
  }, [open, sourceEntityId]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (fromId === "" || toId === "") {
      setError("請選擇來源和目標實體");
      return;
    }
    if (!relationType.trim()) {
      setError("請輸入關係類型");
      return;
    }
    if (fromId === toId) {
      setError("不能建立自我關聯");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        from_entity_id: Number(fromId),
        to_entity_id: Number(toId),
        relation_type: relationType.trim(),
        description: description.trim(),
      });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">新增關係</h3>

        {error && (
          <div className="mb-3 p-2 bg-red-50 text-red-600 text-sm rounded-lg">
            {error}
          </div>
        )}

        <div className="grid gap-3">
          {/* Source */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              來源實體
            </label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              value={fromId}
              onChange={(e) => setFromId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">選擇實體…</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  [{e.entity_type}] {e.name}
                </option>
              ))}
            </select>
          </div>

          {/* Relation type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              關係類型
            </label>
            <input
              list="relation-types-list"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="例如：作者、合作、引用、指導"
              value={relationType}
              onChange={(e) => setRelationType(e.target.value)}
            />
            <datalist id="relation-types-list">
              {existingTypes.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </div>

          {/* Target */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              目標實體
            </label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              value={toId}
              onChange={(e) => setToId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">選擇實體…</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  [{e.entity_type}] {e.name}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              描述（選填）
            </label>
            <textarea
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y"
              rows={2}
              placeholder="關於這段關係的描述…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>

        {/* Direction indicator */}
        {fromId !== "" && toId !== "" && (
          <div className="mt-3 p-2 bg-gray-50 rounded-lg text-sm text-gray-600 text-center">
            {entities.find((e) => e.id === fromId)?.name ?? "?"}
            <span className="mx-2 text-blue-600 font-medium">
              ──[{relationType || "..."}]──→
            </span>
            {entities.find((e) => e.id === toId)?.name ?? "?"}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "儲存中..." : "建立關係"}
          </button>
        </div>
      </div>
    </div>
  );
}
