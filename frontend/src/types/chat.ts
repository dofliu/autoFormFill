/** A single message in the conversation. */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
}

/** A retrieved document chunk with metadata. */
export interface SourceChunk {
  text: string;
  metadata: Record<string, string>;
  distance: number | null;
  collection: string;
}

/** Request body sent to POST /api/v1/chat. */
export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
  collections?: string[];
  n_results?: number;
}

// --- SSE event types ---

export interface SSESourcesEvent {
  type: "sources";
  sources: SourceChunk[];
}

export interface SSEChunkEvent {
  type: "chunk";
  content: string;
}

export interface SSEDoneEvent {
  type: "done";
}

export interface SSEErrorEvent {
  type: "error";
  message: string;
}

export type SSEEvent =
  | SSESourcesEvent
  | SSEChunkEvent
  | SSEDoneEvent
  | SSEErrorEvent;
