/**
 * Memory-related API
 * Uses the generic requestJson helper.
 */
import { requestJson } from "./api";

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

export type MemoryRetrievalHit = {
  memory_id: string;
  score: number;
  summary_text: string;
  summary_digest: string;
  matched_terms: string[];
  match_reasons: string[];
  lineage_refs: string[];
  enhancement: Record<string, unknown>;
};

export async function getSessionMemorySummary(token: string): Promise<SessionMemorySummary> {
  return requestJson<SessionMemorySummary>("/api/memory/session/summary", token, {
    method: "GET",
  });
}

export async function listMemories(
  token: string,
  includeDisabled = false
): Promise<{ items: AgentMemoryRecord[] }> {
  const query = includeDisabled ? "?include_disabled=true" : "";
  return requestJson<{ items: AgentMemoryRecord[] }>(`/api/memories${query}`, token, {
    method: "GET",
  });
}

export async function clearSessionMemory(
  token: string
): Promise<{ cleared: boolean; entry_count: number }> {
  return requestJson<{ cleared: boolean; entry_count: number }>("/api/memory/session", token, {
    method: "DELETE",
  });
}

export async function promoteSessionMemory(token: string): Promise<AgentMemoryRecord> {
  return requestJson<AgentMemoryRecord>("/api/memories/promote", token, {
    method: "POST",
  });
}

export async function disableMemory(memoryId: string, token: string): Promise<AgentMemoryRecord> {
  return requestJson<AgentMemoryRecord>(
    `/api/memories/${encodeURIComponent(memoryId)}/disable`,
    token,
    { method: "POST" }
  );
}

export async function retrieveMemories(
  query: string,
  token: string,
  limit = 5
): Promise<{ items: MemoryRetrievalHit[] }> {
  return requestJson<{ items: MemoryRetrievalHit[] }>("/api/memories/retrieve", token, {
    method: "POST",
    body: { query, limit },
  });
}
