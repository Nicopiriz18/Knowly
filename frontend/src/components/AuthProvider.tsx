"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Me, getMe } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

const PUBLIC_PATHS = ["/login"];

interface AuthContextValue {
  user: Me | null;
  refresh: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  refresh: async () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<Me | null>(null);
  const [checked, setChecked] = useState(false);

  const isPublic = PUBLIC_PATHS.includes(pathname);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      setUser(await getMe());
    } catch {
      clearToken();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setChecked(true));
  }, [refresh]);

  useEffect(() => {
    if (!checked) return;
    if (!user && !isPublic) router.replace("/login");
    else if (pathname === "/admin" && user && !user.is_admin) router.replace("/");
  }, [checked, user, isPublic, pathname, router]);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    router.replace("/login");
  }, [router]);

  const blocked = !checked || (!user && !isPublic) || (pathname === "/admin" && !user?.is_admin);

  return (
    <AuthContext.Provider value={{ user, refresh, logout }}>
      {blocked && !isPublic ? (
        <div className="h-screen flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-gray-600 animate-spin" />
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}
