/**
 * Suggestion-related API
 * Uses the generic requestJson helper.
 */
import { requestJson } from "./api";

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
  return requestJson<{ items: AgentProfileSuggestion[] }>("/api/profile/suggestions", token, {
    method: "GET",
  });
}

export async function generateSuggestions(
  token: string
): Promise<{ items: AgentProfileSuggestion[] }> {
  return requestJson<{ items: AgentProfileSuggestion[] }>(
    "/api/profile/suggestions/generate",
    token,
    { method: "POST" }
  );
}

export async function applySuggestion(
  suggestionId: string,
  token: string
): Promise<{ applied: boolean; suggestion: AgentProfileSuggestion }> {
  return requestJson<{ applied: boolean; suggestion: AgentProfileSuggestion }>(
    `/api/profile/suggestions/${encodeURIComponent(suggestionId)}/apply`,
    token,
    { method: "POST" }
  );
}

export async function dismissSuggestion(
  suggestionId: string,
  token: string
): Promise<{ dismissed: boolean; suggestion: AgentProfileSuggestion }> {
  return requestJson<{ dismissed: boolean; suggestion: AgentProfileSuggestion }>(
    `/api/profile/suggestions/${encodeURIComponent(suggestionId)}/dismiss`,
    token,
    { method: "POST" }
  );
}
