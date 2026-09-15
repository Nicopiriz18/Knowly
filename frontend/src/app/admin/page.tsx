"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, Check, Loader2, ShieldCheck, X } from "lucide-react";
import { UserInfo, UserStatus, getUsers, updateUserStatus } from "@/lib/api";

const TABS: { key: UserStatus; label: string }[] = [
  { key: "pending", label: "Pendientes" },
  { key: "approved", label: "Con acceso" },
  { key: "rejected", label: "Rechazados" },
];

function formatDate(ts: number | null) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

export default function AdminPage() {
  const [tab, setTab] = useState<UserStatus>("pending");
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await getUsers());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los usuarios.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const changeStatus = async (email: string, status: "approved" | "rejected") => {
    setBusy(email);
    setError(null);
    try {
      const updated = await updateUserStatus(email, status);
      setUsers((prev) => prev.map((u) => (u.email === email ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar el usuario.");
    } finally {
      setBusy(null);
    }
  };

  const counts = Object.fromEntries(
    TABS.map((t) => [t.key, users.filter((u) => u.status === t.key).length])
  ) as Record<UserStatus, number>;
  const visible = users.filter((u) => u.status === tab);

  return (
    <main className="min-h-screen p-6 md:p-10">
      <div className="max-w-3xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al chat
        </Link>

        <div className="flex items-center gap-2.5 mb-6">
          <ShieldCheck className="w-6 h-6 text-indigo-500" />
          <h1 className="text-xl font-semibold text-white">Solicitudes de acceso</h1>
        </div>

        <div className="flex gap-1 mb-4 border-b border-gray-800">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t.key
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {t.label}
              <span className="ml-2 text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{counts[t.key]}</span>
            </button>
          ))}
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-xl p-3 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-5 h-5 text-gray-600 animate-spin" />
          </div>
        ) : visible.length === 0 ? (
          <p className="text-sm text-gray-600 text-center py-12">No hay usuarios en esta lista.</p>
        ) : (
          <ul className="bg-gray-900 border border-gray-800 rounded-2xl divide-y divide-gray-800">
            {visible.map((u) => (
              <li key={u.email} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="flex-1 min-w-[200px]">
                  <p className="text-sm text-gray-200 break-all">
                    {u.email}
                    {u.is_admin && (
                      <span className="ml-2 text-[10px] uppercase tracking-wide bg-indigo-600/20 text-indigo-400 px-1.5 py-0.5 rounded">
                        admin
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-gray-600 mt-0.5">
                    Solicitado {formatDate(u.created_at)}
                    {u.decided_at && u.status !== "pending" && ` · Actualizado ${formatDate(u.decided_at)}`}
                  </p>
                </div>

                {!u.is_admin && (
                  <div className="flex gap-2">
                    {busy === u.email ? (
                      <Loader2 className="w-4 h-4 text-gray-500 animate-spin" />
                    ) : (
                      <>
                        {u.status !== "approved" && (
                          <button
                            onClick={() => changeStatus(u.email, "approved")}
                            className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-green-600/15 text-green-400 hover:bg-green-600/25 transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" /> Aprobar
                          </button>
                        )}
                        {u.status !== "rejected" && (
                          <button
                            onClick={() => changeStatus(u.email, "rejected")}
                            className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-red-600/10 text-red-400 hover:bg-red-600/20 transition-colors"
                          >
                            <X className="w-3.5 h-3.5" /> {u.status === "approved" ? "Revocar" : "Rechazar"}
                          </button>
                        )}
                      </>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
