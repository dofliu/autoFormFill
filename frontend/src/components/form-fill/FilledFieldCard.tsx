import { useState } from "react";
import type { FieldFillResult } from "../../types/form";
import { sourceLabel, sourceColor, confidencePercent } from "../../utils/formatters";

interface Props {
  result: FieldFillResult;
  editedValue: string;
  onValueChange: (value: string) => void;
  onReset: () => void;
}

export default function FilledFieldCard({ result, editedValue, onValueChange, onReset }: Props) {
  const [expanded, setExpanded] = useState(result.source === "skip" || result.source === "rag");
  const colors = sourceColor(result.source);
  const isManual = result.value === "[需人工補充]";
  const isModified = editedValue !== result.value;

  return (
    <div
      id={`field-${result.field_name}`}
      className={`border border-gray-200 rounded-lg ${colors.border} border-l-4 bg-white`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm text-gray-800">{result.field_name}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${colors.bg} ${colors.text}`}>
            {sourceLabel(result.source)}
          </span>
          {isModified && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
              已修改
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {result.source !== "skip" && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <div className="w-16 h-1.5 bg-gray-200 rounded-full">
                <div
                  className={`h-full rounded-full ${
                    result.confidence > 0.7
                      ? "bg-green-500"
                      : result.confidence > 0.4
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${Math.round(result.confidence * 100)}%` }}
                />
              </div>
              <span>{confidencePercent(result.confidence)}</span>
            </div>
          )}
          <span className="text-gray-400 text-xs">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div className="px-4 pb-3 border-t border-gray-100 pt-2">
          <textarea
            className={`w-full border rounded-lg px-3 py-2 text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none ${
              isManual ? "border-red-300 bg-red-50" : "border-gray-200"
            }`}
            rows={Math.max(2, Math.ceil(editedValue.length / 60))}
            value={editedValue}
            onChange={(e) => onValueChange(e.target.value)}
            placeholder={isManual ? "請手動填寫此欄位..." : ""}
          />
          {isModified && (
            <div className="flex justify-end mt-1">
              <button
                onClick={onReset}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                還原原始值
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
