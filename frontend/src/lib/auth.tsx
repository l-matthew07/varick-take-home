"use client";

import { createContext, useContext } from "react";

import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
}

const AuthContext = createContext<AuthContextValue>({ user: null });

export const AuthProvider = AuthContext.Provider;

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
