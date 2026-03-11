const BASE_URL = "/api/v1/auth";

export interface AuthUser {
  id: number;
  email: string | null;
  name_zh: string | null;
  name_en: string | null;
  role: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof body.detail === "object" ? body.detail.detail : body.detail;
    throw new Error(detail || "Login failed");
  }
  return res.json();
}

export async function registerApi(
  email: string,
  password: string,
  name_zh?: string,
  name_en?: string,
): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name_zh, name_en }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof body.detail === "object" ? body.detail.detail : body.detail;
    throw new Error(detail || "Registration failed");
  }
  return res.json();
}

export async function refreshTokenApi(refreshToken: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    throw new Error("Token refresh failed");
  }
  return res.json();
}

export async function getMeApi(accessToken: string): Promise<AuthUser> {
  const res = await fetch(`${BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch user info");
  }
  return res.json();
}
