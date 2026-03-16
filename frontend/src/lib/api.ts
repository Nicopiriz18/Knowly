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
  status: "pending" | "downloading" | "transcribing" | "embedding" | "done" | "error";
  message: string;
  progress: number;
}

// ---------------------------------------------------------------------------
// Materias
// ---------------------------------------------------------------------------

export async function getMaterias(): Promise<MateriaInfo[]> {
  const res = await fetch(`${API}/materias`, { cache: "no-store" });
  return res.json();
}

export async function createMateria(title: string): Promise<MateriaInfo> {
  const res = await fetch(`${API}/materias`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Error creating materia");
  }
  return res.json();
}

export async function deleteMateria(materiaId: string): Promise<void> {
  await fetch(`${API}/materias/${materiaId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Classes
// ---------------------------------------------------------------------------

export async function getClasses(materiaId?: string): Promise<ClassInfo[]> {
  const params = materiaId ? `?materia_id=${encodeURIComponent(materiaId)}` : "";
  const res = await fetch(`${API}/classes${params}`, { cache: "no-store" });
  return res.json();
}

export async function deleteClass(classId: string): Promise<void> {
  await fetch(`${API}/classes/${classId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Ingest
// ---------------------------------------------------------------------------

export async function startIngest(
  url: string,
  title: string,
  materiaId: string
): Promise<string> {
  const res = await fetch(`${API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title, materia_id: materiaId }),
  });
  const data = await res.json();
  return data.job_id;
}

export async function getIngestStatus(jobId: string): Promise<IngestStatus> {
  const res = await fetch(`${API}/ingest/${jobId}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function chat(
  query: string,
  classId?: string,
  materiaId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      class_id: classId || null,
      materia_id: materiaId || null,
    }),
  });
  return res.json();
}

export function chatStream(
  query: string,
  classId?: string,
  materiaId?: string
): { url: string; body: string } {
  return {
    url: `${API}/chat/stream`,
    body: JSON.stringify({
      query,
      class_id: classId || null,
      materia_id: materiaId || null,
    }),
  };
}

export { API };
