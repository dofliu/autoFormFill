import { useState } from "react";
import type { FormFillResponse } from "../../types/form";
import FilledFieldCard from "./FilledFieldCard";
import { getDownloadUrl } from "../../api/forms";
import { sourceColor } from "../../utils/formatters";

interface Props {
  response: FormFillResponse;
  onReset: () => void;
}

export default function FieldReviewPanel({ response, onReset }: Props) {
  const [editedValues, setEditedValues] = useState<Map<string, string>>(() => {
    const map = new Map<string, string>();
    response.results.forEach((r) => map.set(r.field_name, r.value));
    return map;
  });

  const updateValue = (fieldName: string, value: string) => {
    setEditedValues((prev) => new Map(prev).set(fieldName, value));
  };

  const resetValue = (fieldName: string) => {
    const original = response.results.find((r) => r.field_name === fieldName);
    if (original) {
      setEditedValues((prev) => new Map(prev).set(fieldName, original.value));
    }
  };

  const scrollToField = (fieldName: string) => {
    document.getElementById(`field-${fieldName}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const sqlCount = response.results.filter((r) => r.source === "sql").length;
  const ragCount = response.results.filter((r) => r.source === "rag").length;
  const skipCount = response.results.filter((r) => r.source === "skip").length;

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = getDownloadUrl(response.filename);
    a.download = response.filename;
    a.click();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <button
            onClick={onReset}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← 返回
          </button>
          <h2 className="text-base font-semibold text-gray-800">表單審查</h2>
        </div>
        <div className="text-xs text-gray-500">
          共 {response.results.length} 個欄位
        </div>
      </div>

      {/* Split view */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Field list */}
        <div className="w-2/5 border-r border-gray-200 overflow-y-auto p-4">
          <h3 className="text-sm font-medium text-gray-500 mb-3">偵測到的欄位</h3>
          <div className="space-y-1">
            {response.results.map((r) => {
              const colors = sourceColor(r.source);
              return (
                <button
                  key={r.field_name}
                  onClick={() => scrollToField(r.field_name)}
                  className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  <span className={`w-2 h-2 rounded-full ${colors.bg}`} />
                  <span className="flex-1 text-gray-700">{r.field_name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                    {r.source}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Filled cards */}
        <div className="w-3/5 overflow-y-auto p-4 space-y-3">
          <h3 className="text-sm font-medium text-gray-500 mb-3">AI 填寫結果</h3>
          {response.results.map((r) => (
            <FilledFieldCard
              key={r.field_name}
              result={r}
              editedValue={editedValues.get(r.field_name) || ""}
              onValueChange={(v) => updateValue(r.field_name, v)}
              onReset={() => resetValue(r.field_name)}
            />
          ))}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            SQL 資料: {sqlCount}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            AI 生成: {ragCount}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            需人工: {skipCount}
          </span>
        </div>
        <button
          onClick={handleDownload}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <span>⬇</span> 下載填寫結果
        </button>
      </div>
    </div>
  );
}
