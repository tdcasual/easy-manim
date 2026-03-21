function apiBaseUrl(): string {
  const base = (import.meta as any).env?.VITE_API_BASE_URL;
  return typeof base === "string" ? base.replace(/\/+$/, "") : "";
}

async function requestJson<T>(path: string, init: RequestInit, token: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");
  headers.set("authorization", `Bearer ${token}`);
  if (init.body) headers.set("content-type", "application/json");

  const response = await fetch(`${apiBaseUrl()}${path}`, { ...init, headers });
  const text = await response.text().catch(() => "");
  if (!response.ok) throw new Error(`http_${response.status}:${text || response.statusText}`);
  return (text ? JSON.parse(text) : {}) as T;
}

export type SessionMemorySummary = {
  session_id: string;
  agent_id?: string | null;
  entry_count: number;
  summary_text: string;
  summary_digest?: string | null;
  lineage_refs?: string[];
  entries?: unknown[];
};

export type AgentMemoryRecord = {
  memory_id: string;
  agent_id: string;
  source_session_id: string;
  status: string;
  summary_text: string;
  summary_digest: string;
  lineage_refs: string[];
  created_at: string;
  disabled_at?: string | null;
};

export async function getSessionMemorySummary(token: string): Promise<SessionMemorySummary> {
  return requestJson<SessionMemorySummary>("/api/memory/session/summary", { method: "GET" }, token);
}

export async function listMemories(token: string, includeDisabled = false): Promise<{ items: AgentMemoryRecord[] }> {
  const q = includeDisabled ? "?include_disabled=true" : "";
  return requestJson<{ items: AgentMemoryRecord[] }>(`/api/memories${q}`, { method: "GET" }, token);
}

export async function clearSessionMemory(token: string): Promise<{ cleared: boolean; entry_count: number }> {
  return requestJson<{ cleared: boolean; entry_count: number }>(
    "/api/memory/session",
    { method: "DELETE" },
    token
  );
}

export async function promoteSessionMemory(token: string): Promise<AgentMemoryRecord> {
  return requestJson<AgentMemoryRecord>("/api/memories/promote", { method: "POST" }, token);
}

export async function disableMemory(memoryId: string, token: string): Promise<AgentMemoryRecord> {
  return requestJson<AgentMemoryRecord>(
    `/api/memories/${encodeURIComponent(memoryId)}/disable`,
    { method: "POST" },
    token
  );
}
