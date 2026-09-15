"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Clock, GraduationCap, Loader2, Mail } from "lucide-react";
import { startLogin, verifyLogin } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { useAuth } from "@/components/AuthProvider";

type Step = "email" | "code" | "pending";

const inputClass =
  "w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors";

export default function LoginPage() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  const submitEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { status } = await startLogin(email.trim());
      setStep(status === "otp_sent" ? "code" : "pending");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo continuar.");
    } finally {
      setLoading(false);
    }
  };

  const submitCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { token } = await verifyLogin(email.trim(), code);
      setToken(token);
      await refresh();
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Código inválido.");
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    setError(null);
    setCode("");
    try {
      await startLogin(email.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo reenviar el código.");
    }
  };

  const back = () => {
    setStep("email");
    setCode("");
    setError(null);
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <GraduationCap className="w-8 h-8 text-indigo-500" />
          <h1 className="text-2xl font-bold text-white">Knowly</h1>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          {step === "email" && (
            <form onSubmit={submitEmail} className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Ingresar</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Si ya tenés acceso te enviamos un código. Si no, registramos tu solicitud.
                </p>
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@mail.com"
                required
                autoFocus
                autoComplete="email"
                className={inputClass}
              />
              {error && <ErrorBox message={error} />}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-500 text-white text-sm font-medium py-2.5 rounded-xl transition-colors"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                Continuar
              </button>
            </form>
          )}

          {step === "code" && (
            <form onSubmit={submitCode} className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Revisá tu mail</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Enviamos un código de 6 dígitos a <span className="text-gray-300">{email}</span>.
                </p>
              </div>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="\d{6}"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                required
                autoFocus
                className={`${inputClass} text-center text-xl tracking-[0.5em] font-mono`}
              />
              {error && <ErrorBox message={error} />}
              <button
                type="submit"
                disabled={loading || code.length !== 6}
                className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-500 text-white text-sm font-medium py-2.5 rounded-xl transition-colors"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Ingresar
              </button>
              <div className="flex justify-between text-xs">
                <button type="button" onClick={back} className="text-gray-500 hover:text-gray-300 inline-flex items-center gap-1">
                  <ArrowLeft className="w-3 h-3" /> Cambiar mail
                </button>
                <button type="button" onClick={resend} className="text-indigo-400 hover:text-indigo-300">
                  Reenviar código
                </button>
              </div>
            </form>
          )}

          {step === "pending" && (
            <div className="text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-amber-500/10 flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Solicitud pendiente</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Registramos tu pedido de acceso para <span className="text-gray-300">{email}</span>.
                  Te avisamos por mail cuando sea aprobado.
                </p>
              </div>
              <button onClick={back} className="text-xs text-gray-500 hover:text-gray-300 inline-flex items-center gap-1">
                <ArrowLeft className="w-3 h-3" /> Usar otro mail
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-xl p-3">
      <AlertCircle className="w-4 h-4 shrink-0" />
      {message}
    </div>
  );
}
