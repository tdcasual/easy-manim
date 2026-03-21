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

export type EvalCaseResult = {
  task_id: string;
  root_task_id: string;
  status: string;
  duration_seconds: number;
  tags?: string[];
  issue_codes?: string[];
  quality_issue_codes?: string[];
  quality_score?: number;
  repair_attempted?: boolean;
  repair_success?: boolean;
  repair_stop_reason?: string | null;
  manual_review_required?: boolean;
  risk_domains?: string[];
  review_focus?: string[];
};

export type EvalRunSummary = {
  run_id: string;
  suite_id: string;
  provider: string;
  total_cases: number;
  items?: EvalCaseResult[];
  report?: Record<string, unknown>;
};

export async function listEvals(token: string): Promise<{ items: EvalRunSummary[] }> {
  return requestJson<{ items: EvalRunSummary[] }>("/api/profile/evals", { method: "GET" }, token);
}

export async function getEval(runId: string, token: string): Promise<EvalRunSummary> {
  return requestJson<EvalRunSummary>(`/api/profile/evals/${encodeURIComponent(runId)}`, { method: "GET" }, token);
}
