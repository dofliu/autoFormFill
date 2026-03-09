const BASE_URL = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: string;
  code: string;
  field: string | null;

  constructor(status: number, detail: string, code: string = "unknown", field: string | null = null) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.code = code;
    this.field = field;
  }
}

/**
 * Parse error body from API response.
 * Handles both old format `{detail: "string"}` and new structured format
 * `{detail: {detail, code, field}}`.
 */
function parseErrorBody(body: Record<string, unknown>): { detail: string; code: string; field: string | null } {
  const raw = body.detail;
  if (typeof raw === "object" && raw !== null) {
    const structured = raw as Record<string, unknown>;
    return {
      detail: String(structured.detail || "Unknown error"),
      code: String(structured.code || "unknown"),
      field: structured.field ? String(structured.field) : null,
    };
  }
  return { detail: String(raw || "Unknown error"), code: "unknown", field: null };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const parsed = parseErrorBody(body);
    throw new ApiError(res.status, parsed.detail, parsed.code, parsed.field);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function postForm<T>(path: string, formData: FormData): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type — browser sets boundary for multipart
  });
}

export function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function del(path: string): Promise<void> {
  return request<void>(path, { method: "DELETE" });
}

export function downloadUrl(filename: string): string {
  return `${BASE_URL}/forms/download/${encodeURIComponent(filename)}`;
}
