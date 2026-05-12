"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import * as api from "@/lib/api";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = api.getToken();
    setTokenState(storedToken);

    if (!storedToken) {
      setLoading(false);
      return;
    }

    api
      .getMe()
      .then(setUser)
      .catch(() => {
        api.clearToken();
        setTokenState(null);
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.login(email, password);
    api.setToken(response.access_token);
    setTokenState(response.access_token);
    const currentUser = await api.getMe();
    setUser(currentUser);
  }, []);

  const logout = useCallback(() => {
    api.clearToken();
    setTokenState(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, login, logout, loading }),
    [user, token, login, logout, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
