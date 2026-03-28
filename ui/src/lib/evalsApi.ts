/**
 * 评估相关 API
 * 使用通用 requestJson 函数
 */
import { requestJson } from "./api";

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
  return requestJson<{ items: EvalRunSummary[] }>("/api/profile/evals", token, {
    method: "GET",
  });
}

export async function getEval(runId: string, token: string): Promise<EvalRunSummary> {
  return requestJson<EvalRunSummary>(`/api/profile/evals/${encodeURIComponent(runId)}`, token, {
    method: "GET",
  });
}
