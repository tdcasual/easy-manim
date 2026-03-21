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

export type AgentProfile = {
  agent_id: string;
  name: string;
  status: string;
  profile_version: number;
  profile_json: Record<string, unknown>;
  policy_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ProfileScorecard = {
  completed_count: number;
  failed_count: number;
  failed_count_recent: number;
  median_quality_score: number;
  top_issue_codes: string[];
  recent_profile_digests: string[];
};

export async function getProfile(token: string): Promise<AgentProfile> {
  return requestJson<AgentProfile>("/api/profile", { method: "GET" }, token);
}

export async function getProfileScorecard(token: string): Promise<ProfileScorecard> {
  return requestJson<ProfileScorecard>("/api/profile/scorecard", { method: "GET" }, token);
}

export async function applyProfilePatch(patch: Record<string, unknown>, token: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    "/api/profile/apply",
    { method: "POST", body: JSON.stringify({ patch }) },
    token
  );
}
