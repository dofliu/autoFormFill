import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { AuthUser, TokenResponse } from "../api/auth";
import { loginApi, registerApi, refreshTokenApi } from "../api/auth";

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, nameZh?: string, nameEn?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY_ACCESS = "smartfill_access_token";
const STORAGE_KEY_REFRESH = "smartfill_refresh_token";
const STORAGE_KEY_USER = "smartfill_user";

function saveTokens(data: TokenResponse) {
  localStorage.setItem(STORAGE_KEY_ACCESS, data.access_token);
  localStorage.setItem(STORAGE_KEY_REFRESH, data.refresh_token);
  localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(data.user));
  // Backward compatibility: keep smartfill_user_id for any remaining references
  localStorage.setItem("smartfill_user_id", String(data.user.id));
}

function clearTokens() {
  localStorage.removeItem(STORAGE_KEY_ACCESS);
  localStorage.removeItem(STORAGE_KEY_REFRESH);
  localStorage.removeItem(STORAGE_KEY_USER);
  localStorage.removeItem("smartfill_user_id");
}

function loadStoredAuth(): { user: AuthUser | null; accessToken: string | null; refreshToken: string | null } {
  const accessToken = localStorage.getItem(STORAGE_KEY_ACCESS);
  const refreshToken = localStorage.getItem(STORAGE_KEY_REFRESH);
  const userStr = localStorage.getItem(STORAGE_KEY_USER);
  let user: AuthUser | null = null;
  if (userStr) {
    try {
      user = JSON.parse(userStr);
    } catch {
      user = null;
    }
  }
  return { user, accessToken, refreshToken };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = loadStoredAuth();
  const [user, setUser] = useState<AuthUser | null>(stored.user);
  const [accessToken, setAccessToken] = useState<string | null>(stored.accessToken);
  const [refreshToken, setRefreshToken] = useState<string | null>(stored.refreshToken);
  const [isLoading, setIsLoading] = useState(false);

  const handleTokenResponse = useCallback((data: TokenResponse) => {
    setUser(data.user);
    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
    saveTokens(data);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await loginApi(email, password);
      handleTokenResponse(data);
    } finally {
      setIsLoading(false);
    }
  }, [handleTokenResponse]);

  const register = useCallback(async (email: string, password: string, nameZh?: string, nameEn?: string) => {
    setIsLoading(true);
    try {
      const data = await registerApi(email, password, nameZh, nameEn);
      handleTokenResponse(data);
    } finally {
      setIsLoading(false);
    }
  }, [handleTokenResponse]);

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    clearTokens();
  }, []);

  // Try refresh on mount if we have a refresh token but no valid access token
  useEffect(() => {
    if (!accessToken && refreshToken) {
      setIsLoading(true);
      refreshTokenApi(refreshToken)
        .then((data) => handleTokenResponse(data))
        .catch(() => {
          // Refresh failed — clear everything
          logout();
        })
        .finally(() => setIsLoading(false));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value: AuthContextType = {
    user,
    accessToken,
    refreshToken,
    isAuthenticated: !!user && !!accessToken,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
