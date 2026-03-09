import { useRef, useState } from "react";
import { streamEmailDraft } from "../api/email";
import type { SourceChunk } from "../types/chat";
import type { EmailDraftRequest } from "../types/email";

const TONE_OPTIONS = [
  { value: "professional", label: "專業 (Professional)" },
  { value: "friendly", label: "親切 (Friendly)" },
  { value: "formal", label: "正式 (Formal)" },
] as const;

const COLLECTION_COLORS: Record<string, string> = {
  academic_papers: "bg-blue-100 text-blue-800",
  research_projects: "bg-green-100 text-green-800",
  auto_indexed: "bg-amber-100 text-amber-800",
};

export default function EmailDraftPage() {
  // Form state
  const [recipientName, setRecipientName] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [subjectHint, setSubjectHint] = useState("");
  const [purpose, setPurpose] = useState("");
  const [tone, setTone] = useState<"professional" | "friendly" | "formal">(
    "professional",
  );

  // Draft state
  const [draft, setDraft] = useState("");
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [showSources, setShowSources] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const draftRef = useRef<HTMLDivElement>(null);

  const canGenerate =
    recipientName.trim() && recipientEmail.trim() && purpose.trim();

  async function handleGenerate() {
    if (!canGenerate || isStreaming) return;

    // Reset state
    setDraft("");
    setSources([]);
    setShowSources(false);
    setError(null);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const request: EmailDraftRequest = {
      recipient_name: recipientName.trim(),
      recipient_email: recipientEmail.trim(),
      subject_hint: subjectHint.trim() || undefined,
      purpose: purpose.trim(),
      tone,
    };

    try {
      for await (const event of streamEmailDraft(
        request,
        controller.signal,
      )) {
        switch (event.type) {
          case "sources":
            setSources(event.sources);
            break;
          case "chunk":
            setDraft((prev) => prev + event.content);
            // Auto-scroll to bottom of draft
            if (draftRef.current) {
              draftRef.current.scrollTop = draftRef.current.scrollHeight;
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
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(draft);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = draft;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    }
  }

  function handleDownload() {
    if (!draft) return;
    const header = `To: ${recipientEmail}\nSubject: ${subjectHint || "(未指定)"}\n${"─".repeat(40)}\n\n`;
    const blob = new Blob([header + draft], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `email_draft_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleClear() {
    setDraft("");
    setSources([]);
    setShowSources(false);
    setError(null);
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-800">郵件草稿生成</h1>
        <p className="text-sm text-gray-500 mt-1">
          輸入收件人與目的，從知識庫生成專業郵件草稿
        </p>
      </div>

      {/* Main content — split view */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Input form */}
        <div className="w-80 shrink-0 border-r border-gray-200 p-5 overflow-y-auto">
          <div className="space-y-4">
            {/* Recipient name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                收件人姓名 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="例：王教授"
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
            </div>

            {/* Recipient email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                收件人信箱 <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                placeholder="例：wang@ntu.edu.tw"
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
            </div>

            {/* Subject hint */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                主旨提示
              </label>
              <input
                type="text"
                value={subjectHint}
                onChange={(e) => setSubjectHint(e.target.value)}
                placeholder="例：研究合作邀請"
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
            </div>

            {/* Purpose */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                郵件目的 <span className="text-red-500">*</span>
              </label>
              <textarea
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="描述你想寫這封信的目的，例如：&#10;「邀請王教授參與我們的 AI 研究計畫合作」"
                disabled={isStreaming}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 resize-none"
              />
            </div>

            {/* Tone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                語氣
              </label>
              <select
                value={tone}
                onChange={(e) =>
                  setTone(
                    e.target.value as "professional" | "friendly" | "formal",
                  )
                }
                disabled={isStreaming}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                {TONE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
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
                  ✨ 生成草稿
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right: Draft preview */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Draft content */}
          <div
            ref={draftRef}
            className="flex-1 p-6 overflow-y-auto"
          >
            {!draft && !isStreaming && !error && (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <div className="text-5xl mb-4">✉️</div>
                  <p className="text-lg">填寫左側表單，生成郵件草稿</p>
                  <p className="text-sm mt-2">
                    系統會從知識庫檢索相關資料，生成專業信件
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

            {/* Draft text */}
            {(draft || isStreaming) && (
              <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
                  <span className="text-gray-400">To:</span>
                  <span className="text-gray-700">
                    {recipientName} &lt;{recipientEmail}&gt;
                  </span>
                </div>
                {subjectHint && (
                  <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
                    <span className="text-gray-400">Subject:</span>
                    <span className="text-gray-700">{subjectHint}</span>
                  </div>
                )}
                <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                  {draft}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-400 ml-0.5 animate-pulse rounded-sm" />
                  )}
                </div>
                {isStreaming && !draft && (
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
          {draft && !isStreaming && (
            <div className="px-6 py-3 border-t border-gray-200 flex items-center gap-3">
              <button
                onClick={handleCopy}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                {copyFeedback ? "✅ 已複製" : "📋 複製草稿"}
              </button>
              <button
                onClick={handleDownload}
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
