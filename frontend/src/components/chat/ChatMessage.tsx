import { useState } from "react";
import type { ChatMessage as ChatMessageType, SourceChunk } from "../../types/chat";

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

const COLLECTION_COLORS: Record<string, string> = {
  academic_papers: "bg-blue-100 text-blue-800",
  research_projects: "bg-green-100 text-green-800",
  auto_indexed: "bg-amber-100 text-amber-800",
};

function SourceBadge({ source }: { source: SourceChunk }) {
  const colorClass =
    COLLECTION_COLORS[source.collection] || "bg-gray-100 text-gray-800";
  const title =
    source.metadata.title || source.metadata.filename || source.collection;
  const snippet =
    source.text.length > 120
      ? source.text.slice(0, 120) + "..."
      : source.text;

  return (
    <div className="border border-gray-200 rounded-lg p-3 text-sm">
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
        >
          {source.collection}
        </span>
        <span className="font-medium text-gray-700 truncate">{title}</span>
        {source.distance !== null && (
          <span className="text-gray-400 text-xs ml-auto">
            {source.distance.toFixed(3)}
          </span>
        )}
      </div>
      <p className="text-gray-500 text-xs leading-relaxed">{snippet}</p>
    </div>
  );
}

export default function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === "user";
  const hasSources = message.sources && message.sources.length > 0;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-gray-100 text-gray-800 rounded-bl-md"
        }`}
      >
        {/* Message content */}
        <div className="whitespace-pre-wrap break-words">
          {message.content}
          {isStreaming && !isUser && (
            <span className="inline-block w-2 h-4 bg-gray-400 ml-0.5 animate-pulse rounded-sm" />
          )}
        </div>

        {/* Empty state while streaming (no content yet) */}
        {isStreaming && !isUser && !message.content && (
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

        {/* Sources toggle */}
        {!isUser && hasSources && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {showSources
                ? "▼ 隱藏來源"
                : `▶ 顯示 ${message.sources!.length} 個來源`}
            </button>
            {showSources && (
              <div className="mt-2 space-y-2">
                {message.sources!.map((source, i) => (
                  <SourceBadge key={i} source={source} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
