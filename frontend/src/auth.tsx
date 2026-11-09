import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { createApi, type Api } from "./lib/api";

const STORAGE_KEY = "clinic.apiKey";

interface AuthValue {
  apiKey: string | null;
  api: Api | null;
  signIn: (key: string) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

function readStoredKey(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(readStoredKey);

  const signIn = useCallback((key: string) => {
    try {
      sessionStorage.setItem(STORAGE_KEY, key);
    } catch {
      /* private mode: the key then lasts for this page view only */
    }
    setApiKey(key);
  }, []);

  const signOut = useCallback(() => {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* nothing stored */
    }
    setApiKey(null);
  }, []);

  const value = useMemo<AuthValue>(
    () => ({ apiKey, api: apiKey ? createApi(apiKey) : null, signIn, signOut }),
    [apiKey, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
