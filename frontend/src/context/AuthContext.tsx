import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { api, setAuthToken, User } from "@/src/utils/api";
import { registerForPush } from "@/src/utils/push";
import { storage } from "@/src/utils/storage";

const TOKEN_KEY = "auth_token";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const restore = async () => {
      try {
        const token = await storage.secureGet<string | null>(TOKEN_KEY, null);
        if (token) {
          setAuthToken(token);
          const me = await api.get<User>("/auth/me");
          setUser(me);
          registerForPush();
        }
      } catch {
        setAuthToken(null);
        await storage.secureRemove(TOKEN_KEY);
      } finally {
        setLoading(false);
      }
    };
    restore();
  }, []);

  const applyAuth = useCallback(
    async (resp: { token: string; user: User }) => {
      setAuthToken(resp.token);
      await storage.secureSet(TOKEN_KEY, resp.token);
      setUser(resp.user);
      registerForPush();
    },
    [],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const resp = await api.post<{ token: string; user: User }>(
        "/auth/login",
        { email, password },
      );
      await applyAuth(resp);
    },
    [applyAuth],
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const resp = await api.post<{ token: string; user: User }>(
        "/auth/register",
        { email, password, name },
      );
      await applyAuth(resp);
    },
    [applyAuth],
  );

  const logout = useCallback(async () => {
    setAuthToken(null);
    await storage.secureRemove(TOKEN_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, setUser }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
