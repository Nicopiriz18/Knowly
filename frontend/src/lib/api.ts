const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ClassInfo {
  class_id: string;
  class_title: string;
  source_url: string;
  chunk_count: number;
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

export async function getClasses(): Promise<ClassInfo[]> {
  const res = await fetch(`${API}/classes`, { cache: "no-store" });
  return res.json();
}

export async function deleteClass(classId: string): Promise<void> {
  await fetch(`${API}/classes/${classId}`, { method: "DELETE" });
}

export async function startIngest(url: string, title: string, classId: string): Promise<string> {
  const res = await fetch(`${API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title, class_id: classId }),
  });
  const data = await res.json();
  return data.job_id;
}

export async function getIngestStatus(jobId: string): Promise<IngestStatus> {
  const res = await fetch(`${API}/ingest/${jobId}`);
  return res.json();
}

export async function chat(query: string, classId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, class_id: classId || null }),
  });
  return res.json();
}

// Returns info needed for streaming fetch
export function chatStream(query: string, classId?: string): { url: string; body: string } {
  return {
    url: `${API}/chat/stream`,
    body: JSON.stringify({ query, class_id: classId || null }),
  };
}

export { API };
