import { create } from "zustand";

import { api } from "../api/client";
import type { User } from "../types/api";

type AuthState = {
  token: string | null;
  user: User | null;
  initialized: boolean;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const STORAGE_KEY = "ganttbuddy.frontend.auth";

function readStoredToken() {
  return window.localStorage.getItem(STORAGE_KEY);
}

function writeStoredToken(token: string | null) {
  if (token) {
    window.localStorage.setItem(STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: typeof window === "undefined" ? null : readStoredToken(),
  user: null,
  initialized: false,
  bootstrap: async () => {
    const token = get().token;
    if (!token) {
      set({ initialized: true, user: null });
      return;
    }

    try {
      const user = await api.me(token);
      set({ user, initialized: true });
    } catch {
      writeStoredToken(null);
      set({ token: null, user: null, initialized: true });
    }
  },
  login: async (email, password) => {
    const tokenResponse = await api.login(email, password);
    writeStoredToken(tokenResponse.access_token);
    const user = await api.me(tokenResponse.access_token);
    set({ token: tokenResponse.access_token, user, initialized: true });
  },
  logout: () => {
    writeStoredToken(null);
    set({ token: null, user: null, initialized: true });
  },
}));
