import { useEffect, useRef, useState } from "react";
import { streamChat } from "../api/chat";
import ChatMessage from "../components/chat/ChatMessage";
import type { ChatMessage as ChatMessageType, SourceChunk } from "../types/chat";

/** Maximum conversation rounds sent as context to the backend. */
const MAX_CONTEXT_ROUNDS = 5;

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    setError("");
    setInput("");

    // Add user message
    const userMsg: ChatMessageType = { role: "user", content: trimmed };
    const assistantMsg: ChatMessageType = {
      role: "assistant",
      content: "",
      sources: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    // Build history (last N rounds, excluding the new messages)
    const historyForRequest = messages
      .slice(-(MAX_CONTEXT_ROUNDS * 2))
      .map((m) => ({ role: m.role, content: m.content }));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const event of streamChat(
        { message: trimmed, history: historyForRequest },
        controller.signal,
      )) {
        switch (event.type) {
          case "sources":
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                sources: event.sources as SourceChunk[],
              };
              return updated;
            });
            break;

          case "chunk":
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              updated[updated.length - 1] = {
                ...last,
                content: last.content + event.content,
              };
              return updated;
            });
            break;

          case "error":
            setError(event.message);
            break;

          case "done":
            break;
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name !== "AbortError") {
        setError(e instanceof Error ? e.message : "發生錯誤");
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleClear = () => {
    if (isStreaming) return;
    setMessages([]);
    setError("");
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] max-w-4xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">💬 知識問答</h2>
        <button
          onClick={handleClear}
          disabled={isStreaming || messages.length === 0}
          className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40"
        >
          清除對話
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto rounded-xl bg-white border border-gray-200 p-4 mb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <span className="text-5xl mb-4">📚</span>
            <p className="text-lg font-medium">向你的知識庫提問</p>
            <p className="text-sm mt-1">
              上傳文件到知識庫後，即可在此進行語意問答
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            message={msg}
            isStreaming={
              isStreaming && i === messages.length - 1 && msg.role === "assistant"
            }
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-3 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Input area */}
      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="輸入你的問題..."
          disabled={isStreaming}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 text-gray-800"
        />
        {isStreaming ? (
          <button
            onClick={handleStop}
            className="px-5 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors font-medium"
          >
            停止
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-medium"
          >
            發送
          </button>
        )}
      </div>
    </div>
  );
}
