import { useRef, useState } from "react";
import { streamReport } from "../api/report";
import type { SourceChunk } from "../types/chat";
import type { ReportRequest } from "../types/report";

const REPORT_TYPE_OPTIONS = [
  { value: "summary", label: "摘要報告 (Summary)" },
  { value: "detailed", label: "詳細報告 (Detailed)" },
  { value: "executive", label: "主管摘要 (Executive)" },
] as const;

const AUDIENCE_OPTIONS = [
  { value: "academic", label: "學術 (Academic)" },
  { value: "business", label: "商業 (Business)" },
  { value: "general", label: "一般 (General)" },
] as const;

const LANGUAGE_OPTIONS = [
  { value: "zh-TW", label: "繁體中文" },
  { value: "en", label: "English" },
] as const;

const COLLECTION_COLORS: Record<string, string> = {
  academic_papers: "bg-blue-100 text-blue-800",
  research_projects: "bg-green-100 text-green-800",
  auto_indexed: "bg-amber-100 text-amber-800",
};

export default function ReportPage() {
  // Form state
  const [topic, setTopic] = useState("");
  const [reportType, setReportType] = useState<
    "summary" | "detailed" | "executive"
  >("summary");
  const [audience, setAudience] = useState<
    "academic" | "business" | "general"
  >("academic");
  const [language, setLanguage] = useState<"zh-TW" | "en">("zh-TW");
  const [customSections, setCustomSections] = useState("");

  // Report state
  const [report, setReport] = useState("");
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [showSources, setShowSources] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  const canGenerate = topic.trim().length > 0;

  async function handleGenerate() {
    if (!canGenerate || isStreaming) return;

    setReport("");
    setSources([]);
    setShowSources(false);
    setError(null);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const sections = customSections.trim()
      ? customSections
          .trim()
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean)
      : undefined;

    const request: ReportRequest = {
      topic: topic.trim(),
      report_type: reportType,
      target_audience: audience,
      language,
      sections,
    };

    try {
      for await (const event of streamReport(request, controller.signal)) {
        switch (event.type) {
          case "sources":
            setSources(event.sources);
            break;
          case "chunk":
            setReport((prev) => prev + event.content);
            if (reportRef.current) {
              reportRef.current.scrollTop = reportRef.current.scrollHeight;
            }
            break;
          case "done":
            break;
          case "error":
            setError(event.message);
            break;
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message || "生成失敗");
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  async function handleCopy() {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(report);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = report;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    }
  }

  function handleDownloadMd() {
    if (!report) return;
    const header = `# ${topic}\n\n`;
    const blob = new Blob([header + report], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleDownloadTxt() {
    if (!report) return;
    const header = `報告主題：${topic}\n報告類型：${reportType}\n${"─".repeat(40)}\n\n`;
    const blob = new Blob([header + report], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleClear() {
    setReport("");
    setSources([]);
    setShowSources(false);
    setError(null);
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-800">報告生成</h1>
        <p className="text-sm text-gray-500 mt-1">
          指定主題與報告類型，從知識庫生成結構化研究報告
        </p>
      </div>

      {/* Main content — split view */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Input form */}
        <div className="w-80 shrink-0 border-r border-gray-200 p-5 overflow-y-auto">
          <div className="space-y-4">
            {/* Topic */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                報告主題 <span className="text-red-500">*</span>
              </label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder={"例：深度學習在自然語言處理的最新進展與應用"}
                disabled={isStreaming}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 resize-none"
              />
            </div>

            {/* Report type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                報告類型
              </label>
              <select
                value={reportType}
                onChange={(e) =>
                  setReportType(
                    e.target.value as "summary" | "detailed" | "executive",
                  )
                }
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                {REPORT_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Target audience */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                目標讀者
              </label>
              <select
                value={audience}
                onChange={(e) =>
                  setAudience(
                    e.target.value as "academic" | "business" | "general",
                  )
                }
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                {AUDIENCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                輸出語言
              </label>
              <select
                value={language}
                onChange={(e) =>
                  setLanguage(e.target.value as "zh-TW" | "en")
                }
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                {LANGUAGE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Custom sections */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                自訂章節大綱
                <span className="text-gray-400 font-normal ml-1">
                  (選填，每行一個)
                </span>
              </label>
              <textarea
                value={customSections}
                onChange={(e) => setCustomSections(e.target.value)}
                placeholder={"留空使用預設大綱，或每行輸入一個章節：\n摘要\n研究方法\n實驗結果\n結論"}
                disabled={isStreaming}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 resize-none"
              />
            </div>

            {/* Generate button */}
            <div className="pt-2">
              {isStreaming ? (
                <button
                  onClick={handleStop}
                  className="w-full py-2.5 px-4 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  ⏹ 停止生成
                </button>
              ) : (
                <button
                  onClick={handleGenerate}
                  disabled={!canGenerate}
                  className="w-full py-2.5 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  ✨ 生成報告
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right: Report preview */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Report content */}
          <div ref={reportRef} className="flex-1 p-6 overflow-y-auto">
            {!report && !isStreaming && !error && (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <div className="text-5xl mb-4">📊</div>
                  <p className="text-lg">填寫左側表單，生成結構化報告</p>
                  <p className="text-sm mt-2">
                    系統會從知識庫檢索相關資料，按照指定大綱生成報告
                  </p>
                </div>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                ⚠️ {error}
              </div>
            )}

            {/* Report text (markdown-like rendering) */}
            {(report || isStreaming) && (
              <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed whitespace-pre-wrap">
                  {report}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-400 ml-0.5 animate-pulse rounded-sm" />
                  )}
                </div>
                {isStreaming && !report && (
                  <div className="flex items-center gap-1 text-gray-400">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <span
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.15s" }}
                    />
                    <span
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.3s" }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Sources section */}
            {sources.length > 0 && (
              <div className="mt-4">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  {showSources
                    ? `▼ 隱藏來源 (${sources.length})`
                    : `▶ 顯示 ${sources.length} 個來源`}
                </button>
                {showSources && (
                  <div className="mt-2 space-y-2">
                    {sources.map((source, i) => {
                      const colorClass =
                        COLLECTION_COLORS[source.collection] ||
                        "bg-gray-100 text-gray-800";
                      const title =
                        source.metadata.title ||
                        source.metadata.filename ||
                        source.collection;
                      const snippet =
                        source.text.length > 120
                          ? source.text.slice(0, 120) + "..."
                          : source.text;

                      return (
                        <div
                          key={i}
                          className="border border-gray-200 rounded-lg p-3 text-sm"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
                            >
                              {source.collection}
                            </span>
                            <span className="font-medium text-gray-700 truncate">
                              {title}
                            </span>
                            {source.distance !== null && (
                              <span className="text-gray-400 text-xs ml-auto">
                                {source.distance.toFixed(3)}
                              </span>
                            )}
                          </div>
                          <p className="text-gray-500 text-xs leading-relaxed">
                            {snippet}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action buttons footer */}
          {report && !isStreaming && (
            <div className="px-6 py-3 border-t border-gray-200 flex items-center gap-3">
              <button
                onClick={handleCopy}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                {copyFeedback ? "✅ 已複製" : "📋 複製報告"}
              </button>
              <button
                onClick={handleDownloadMd}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                📥 下載 .md
              </button>
              <button
                onClick={handleDownloadTxt}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                📥 下載 .txt
              </button>
              <button
                onClick={handleGenerate}
                className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors"
              >
                🔄 重新生成
              </button>
              <button
                onClick={handleClear}
                className="px-4 py-2 text-gray-500 rounded-lg text-sm hover:bg-gray-100 transition-colors ml-auto"
              >
                清除
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
