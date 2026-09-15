import { clearToken, getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface MateriaInfo {
  materia_id: string;
  title: string;
  class_count: number;
}

export interface ClassInfo {
  class_id: string;
  class_title: string;
  source_url: string;
  chunk_count: number;
  materia_id: string;
}

export interface Source {
  class_title: string;
  start_time: number;
  end_time: number;
  timestamp_link: string;
  text: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export interface IngestStatus {
  status: "pending" | "downloading" | "transcribing" | "extracting_frames" | "analyzing_frames" | "embedding" | "done" | "error";
  message: string;
  progress: number;
}

export interface Me {
  email: string;
  is_admin: boolean;
}

export type UserStatus = "pending" | "approved" | "rejected";

export interface UserInfo {
  email: string;
  status: UserStatus;
  created_at: number;
  decided_at: number | null;
  is_admin: boolean;
}

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

async function errorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return String(data.detail[0].msg).replace(/^Value error, /, "");
    }
  } catch {
    // not JSON
  }
  return `Error ${res.status}`;
}

/** fetch with the session token. Redirects to /login when the session is invalid. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API}${path}`, { ...init, headers, cache: "no-store" });

  if (res.status === 401 && token) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }
  if (!res.ok) {
    throw new Error(await errorMessage(res));
  }
  return res;
}

async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, init);
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export function startLogin(email: string): Promise<{ status: "otp_sent" | "pending" }> {
  return apiJson("/auth/start", { method: "POST", body: JSON.stringify({ email }) });
}

export function verifyLogin(email: string, code: string): Promise<{ token: string }> {
  return apiJson("/auth/verify", { method: "POST", body: JSON.stringify({ email, code }) });
}

export function getMe(): Promise<Me> {
  return apiJson("/auth/me");
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export function getUsers(status?: UserStatus): Promise<UserInfo[]> {
  const params = status ? `?status=${status}` : "";
  return apiJson(`/admin/users${params}`);
}

export function updateUserStatus(email: string, status: "approved" | "rejected"): Promise<UserInfo> {
  return apiJson(`/admin/users/${encodeURIComponent(email)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// ---------------------------------------------------------------------------
// Materias
// ---------------------------------------------------------------------------

export function getMaterias(): Promise<MateriaInfo[]> {
  return apiJson("/materias");
}

export function createMateria(title: string): Promise<MateriaInfo> {
  return apiJson("/materias", { method: "POST", body: JSON.stringify({ title }) });
}

export async function deleteMateria(materiaId: string): Promise<void> {
  await apiFetch(`/materias/${materiaId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Classes
// ---------------------------------------------------------------------------

export function getClasses(materiaId?: string): Promise<ClassInfo[]> {
  const params = materiaId ? `?materia_id=${encodeURIComponent(materiaId)}` : "";
  return apiJson(`/classes${params}`);
}

export async function deleteClass(classId: string): Promise<void> {
  await apiFetch(`/classes/${classId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Ingest
// ---------------------------------------------------------------------------

export async function startIngest(url: string, title: string, materiaId: string): Promise<string> {
  const data = await apiJson<{ job_id: string }>("/ingest", {
    method: "POST",
    body: JSON.stringify({ url, title, materia_id: materiaId }),
  });
  return data.job_id;
}

export function getIngestStatus(jobId: string): Promise<IngestStatus> {
  return apiJson(`/ingest/${jobId}`);
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export function chat(query: string, classId?: string | null, materiaId?: string | null): Promise<ChatResponse> {
  return apiJson("/chat", {
    method: "POST",
    body: JSON.stringify({ query, class_id: classId || null, materia_id: materiaId || null }),
  });
}

export function chatStream(query: string, classId?: string | null, materiaId?: string | null): Promise<Response> {
  return apiFetch("/chat/stream", {
    method: "POST",
    body: JSON.stringify({ query, class_id: classId || null, materia_id: materiaId || null }),
  });
}

export { API };
