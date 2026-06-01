"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { getMe, type UserResponse } from "./api";

interface AuthContextType {
  token: string | null;
  user: UserResponse | null;
  setToken: (token: string | null) => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  user: null,
  setToken: () => {},
  loading: true,
});

function getStoredToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return localStorage.getItem("token");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getStoredToken);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(() => Boolean(getStoredToken()));

  const setToken = useCallback((t: string | null) => {
    setTokenState(t);
    if (t) {
      localStorage.setItem("token", t);
    } else {
      localStorage.removeItem("token");
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }

    getMe(token)
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [token, setToken]);

  return (
    <AuthContext.Provider value={{ token, user, setToken, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
