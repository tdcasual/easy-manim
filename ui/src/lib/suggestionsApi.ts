import { clearSessionToken } from "./session";

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
  if (!response.ok) {
    if (response.status === 401) clearSessionToken();
    throw new Error(`http_${response.status}:${text || response.statusText}`);
  }
  return (text ? JSON.parse(text) : {}) as T;
}

export type AgentProfileSuggestion = {
  suggestion_id: string;
  agent_id: string;
  patch_json: Record<string, unknown>;
  rationale_json: Record<string, unknown>;
  provenance_json: Record<string, unknown>;
  status: string;
  created_at: string;
  applied_at?: string | null;
};

export async function listSuggestions(token: string): Promise<{ items: AgentProfileSuggestion[] }> {
  return requestJson<{ items: AgentProfileSuggestion[] }>("/api/profile/suggestions", { method: "GET" }, token);
}

export async function generateSuggestions(token: string): Promise<{ items: AgentProfileSuggestion[] }> {
  return requestJson<{ items: AgentProfileSuggestion[] }>(
    "/api/profile/suggestions/generate",
    { method: "POST" },
    token
  );
}

export async function applySuggestion(
  suggestionId: string,
  token: string
): Promise<{ applied: boolean; suggestion: AgentProfileSuggestion }> {
  return requestJson<{ applied: boolean; suggestion: AgentProfileSuggestion }>(
    `/api/profile/suggestions/${encodeURIComponent(suggestionId)}/apply`,
    { method: "POST" },
    token
  );
}

export async function dismissSuggestion(
  suggestionId: string,
  token: string
): Promise<{ dismissed: boolean; suggestion: AgentProfileSuggestion }> {
  return requestJson<{ dismissed: boolean; suggestion: AgentProfileSuggestion }>(
    `/api/profile/suggestions/${encodeURIComponent(suggestionId)}/dismiss`,
    { method: "POST" },
    token
  );
}
