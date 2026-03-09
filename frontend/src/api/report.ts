/**
 * Report Generation API client — streams SSE responses from the report endpoint.
 */
import type { SSEEvent } from "../types/chat";
import type { ReportRequest } from "../types/report";

const BASE_URL = "/api/v1";

/**
 * Stream a report generation response from the backend as an async generator.
 *
 * Uses `fetch` + `ReadableStream` to parse SSE events.
 * Pass an `AbortSignal` to support cancellation.
 */
export async function* streamReport(
  request: ReportRequest,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent, void, unknown> {
  const response = await fetch(`${BASE_URL}/report/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(
      (body as { detail?: string }).detail || response.statusText,
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

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const eventBlock of parts) {
        const line = eventBlock.trim();
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6);
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
