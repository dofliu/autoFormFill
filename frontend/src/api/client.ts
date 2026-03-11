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

/** Get the current access token from localStorage. */
function getAccessToken(): string | null {
  return localStorage.getItem("smartfill_access_token");
}

/** Build headers with optional Authorization. */
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Try to refresh the access token using the stored refresh token.
 * Returns true if successful, false otherwise.
 */
async function tryRefresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem("smartfill_refresh_token");
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;

    const data = await res.json();
    localStorage.setItem("smartfill_access_token", data.access_token);
    localStorage.setItem("smartfill_refresh_token", data.refresh_token);
    localStorage.setItem("smartfill_user", JSON.stringify(data.user));
    localStorage.setItem("smartfill_user_id", String(data.user.id));
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  // Merge auth headers
  const existingHeaders = (init?.headers as Record<string, string>) || {};
  const headers = authHeaders(existingHeaders);

  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    // If 401, try refreshing token once
    if (res.status === 401 && !retried) {
      const refreshed = await tryRefresh();
      if (refreshed) {
        return request<T>(path, init, true);
      }
      // Refresh failed — redirect to login
      const token = getAccessToken();
      if (token) {
        // Had a token but it's expired/invalid — clear and redirect
        localStorage.removeItem("smartfill_access_token");
        localStorage.removeItem("smartfill_refresh_token");
        localStorage.removeItem("smartfill_user");
        localStorage.removeItem("smartfill_user_id");
        window.location.href = "/login";
        throw new ApiError(401, "Session expired. Please log in again.", "auth_expired");
      }
    }

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

/** Build headers for SSE streaming requests (Content-Type + optional Bearer token). */
export function sseHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/** Get the current user's ID from localStorage (null when not logged in). */
export function getCurrentUserId(): number | null {
  const raw = localStorage.getItem("smartfill_user_id");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}
