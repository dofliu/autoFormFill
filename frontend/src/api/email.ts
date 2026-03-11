/**
 * Email Draft API client — streams SSE responses from the email endpoint.
 */
import type { SSEEvent } from "../types/chat";
import type { EmailDraftRequest } from "../types/email";
import { getCurrentUserId, sseHeaders } from "./client";

const BASE_URL = "/api/v1";

/**
 * Stream an email draft response from the backend as an async generator.
 *
 * Uses `fetch` + `ReadableStream` to parse SSE events.
 * Pass an `AbortSignal` to support cancellation.
 */
export async function* streamEmailDraft(
  request: EmailDraftRequest,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent, void, unknown> {
  // Inject user_id from auth context if not explicitly provided
  const body: EmailDraftRequest = { ...request };
  if (body.user_id == null) {
    const uid = getCurrentUserId();
    if (uid !== null) body.user_id = uid;
  }

  const response = await fetch(`${BASE_URL}/email/draft`, {
    method: "POST",
    headers: sseHeaders(),
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const respBody = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(
      (respBody as { detail?: string }).detail || response.statusText,
    );
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const parts = buffer.split("\n\n");
      // Last part may be incomplete — keep it in the buffer
      buffer = parts.pop() || "";

      for (const eventBlock of parts) {
        const line = eventBlock.trim();
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6); // Remove "data: " prefix
        try {
          const event = JSON.parse(jsonStr) as SSEEvent;
          yield event;
        } catch {
          // Skip malformed events
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
