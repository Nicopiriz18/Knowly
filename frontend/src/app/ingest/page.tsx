"use client";

import { useEffect, useState, useCallback } from "react";
import { ClassInfo, IngestStatus, getClasses, startIngest, getIngestStatus } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import {
  Download,
  Mic,
  Brain,
  CheckCircle,
  Loader2,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

const STEPS = [
  { key: "downloading", label: "Descargando", icon: Download },
  { key: "transcribing", label: "Transcribiendo", icon: Mic },
  { key: "embedding", label: "Generando embeddings", icon: Brain },
  { key: "done", label: "Listo", icon: CheckCircle },
] as const;

function getStepIndex(status: string): number {
  const idx = STEPS.findIndex((s) => s.key === status);
  return idx === -1 ? -1 : idx;
}

export default function IngestPage() {
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [selectedClass, setSelectedClass] = useState<string | null>(null);

  // Form
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [classId, setClassId] = useState("");

  // Status
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchClasses = useCallback(async () => {
    try {
      const data = await getClasses();
      setClasses(data);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchClasses();
  }, [fetchClasses]);

  // Polling
  useEffect(() => {
    if (!jobId || !polling) return;

    const interval = setInterval(async () => {
      try {
        const s = await getIngestStatus(jobId);
        setStatus(s);
        if (s.status === "done" || s.status === "error") {
          setPolling(false);
          if (s.status === "error") setError(s.message);
          if (s.status === "done") fetchClasses();
        }
      } catch {
        setPolling(false);
        setError("Error al consultar el estado del proceso.");
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, polling, fetchClasses]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !title || !classId) return;

    setError(null);
    setStatus(null);

    try {
      const id = await startIngest(url, title, classId);
      setJobId(id);
      setPolling(true);
      setStatus({ status: "pending", message: "Iniciando...", progress: 0 });
    } catch {
      setError("Error al iniciar la indexacion. Verifica que el backend este corriendo.");
    }
  };

  const currentStepIndex = status ? getStepIndex(status.status) : -1;

  return (
    <div className="flex h-screen">
      <Sidebar
        classes={classes}
        selectedClass={selectedClass}
        onSelectClass={setSelectedClass}
        onRefresh={fetchClasses}
      />

      <main className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
        <div className="w-full max-w-lg">
          {/* Back link */}
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Volver al chat
          </Link>

          {/* Form card */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-6">
              Agregar nueva clase
            </h2>

            {!jobId ? (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    URL de YouTube
                  </label>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    required
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    Titulo de la clase
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Ej: Calculo II - Clase 5"
                    required
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    ID de la clase
                  </label>
                  <input
                    type="text"
                    value={classId}
                    onChange={(e) => setClassId(e.target.value)}
                    placeholder="Ej: calculo-2-clase-5"
                    required
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>

                {error && (
                  <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-xl p-3">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2.5 rounded-xl transition-colors"
                >
                  Indexar clase
                </button>
              </form>
            ) : (
              <div className="space-y-6">
                {/* Progress stepper */}
                <div className="space-y-3">
                  {STEPS.map((step, idx) => {
                    const Icon = step.icon;
                    const isActive = idx === currentStepIndex;
                    const isComplete = idx < currentStepIndex;
                    const isPending = idx > currentStepIndex;
                    const isError =
                      status?.status === "error" && idx === currentStepIndex;

                    return (
                      <div
                        key={step.key}
                        className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
                          isActive
                            ? "bg-indigo-600/10 border border-indigo-500/30"
                            : isComplete
                            ? "bg-green-600/10 border border-green-500/20"
                            : "bg-gray-800/50 border border-gray-800"
                        }`}
                      >
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                            isComplete
                              ? "bg-green-600/20 text-green-400"
                              : isActive
                              ? "bg-indigo-600/20 text-indigo-400"
                              : "bg-gray-800 text-gray-600"
                          }`}
                        >
                          {isComplete ? (
                            <CheckCircle className="w-4 h-4" />
                          ) : isActive && !isError ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Icon className="w-4 h-4" />
                          )}
                        </div>
                        <span
                          className={`text-sm font-medium ${
                            isComplete
                              ? "text-green-400"
                              : isActive
                              ? "text-indigo-400"
                              : isPending
                              ? "text-gray-600"
                              : "text-gray-400"
                          }`}
                        >
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Status message */}
                {status?.message && (
                  <p className="text-xs text-gray-500 text-center">
                    {status.message}
                  </p>
                )}

                {/* Error */}
                {error && (
                  <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-xl p-3">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                )}

                {/* Done */}
                {status?.status === "done" && (
                  <div className="text-center">
                    <p className="text-green-400 text-sm font-medium mb-3">
                      Clase indexada exitosamente!
                    </p>
                    <Link
                      href="/"
                      className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors"
                    >
                      Ir al chat
                    </Link>
                  </div>
                )}

                {/* Reset on error */}
                {status?.status === "error" && (
                  <button
                    onClick={() => {
                      setJobId(null);
                      setStatus(null);
                      setError(null);
                    }}
                    className="w-full bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium py-2.5 rounded-xl transition-colors"
                  >
                    Intentar de nuevo
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
