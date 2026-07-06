import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { UserOut } from "./types";
import { loginRequest, fetchMe, setToken, clearToken, getToken } from "./api";

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserOut>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string): Promise<UserOut> {
    const { access_token } = await loginRequest(email, password);
    setToken(access_token);
    const me = await fetchMe();
    setUser(me);
    return me;
  }

  function logout(): void {
    clearToken();
    setUser(null);
  }

  async function refreshUser(): Promise<void> {
    const me = await fetchMe();
    setUser(me);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
