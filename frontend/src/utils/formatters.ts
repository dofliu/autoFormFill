import type { FieldSource } from "../types/form";

export function confidencePercent(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function sourceLabel(source: FieldSource): string {
  switch (source) {
    case "sql":
      return "SQL 資料";
    case "rag":
      return "AI 生成";
    case "override":
      return "手動覆寫";
    case "skip":
      return "需人工補充";
  }
}

export function sourceColor(source: FieldSource) {
  switch (source) {
    case "sql":
      return { border: "border-green-500", bg: "bg-green-100", text: "text-green-800" };
    case "rag":
      return { border: "border-amber-500", bg: "bg-amber-100", text: "text-amber-800" };
    case "skip":
      return { border: "border-red-500", bg: "bg-red-100", text: "text-red-800" };
    case "override":
      return { border: "border-blue-500", bg: "bg-blue-100", text: "text-blue-800" };
  }
}
