/**
 * Eval-related API
 * Uses the generic requestJson helper.
 */
import { requestJson } from "./api";

export type EvalCaseResult = {
  task_id: string;
  root_task_id: string;
  status: string;
  duration_seconds: number;
  delivery_passed?: boolean;
  quality_passed?: boolean;
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

export type EvalRunReport = Record<string, unknown> & {
  success_rate?: number;
  delivery_rate?: number;
  quality?: {
    pass_rate?: number;
  } | null;
};

export type EvalRunSummary = {
  run_id: string;
  suite_id: string;
  provider: string;
  total_cases: number;
  items?: EvalCaseResult[];
  report?: EvalRunReport;
};

export type StrategyPromotionDecision = {
  approved: boolean;
  reasons: string[];
  deltas: Record<string, number>;
  mode?: string;
  applied?: boolean;
  recorded_at?: string | null;
};

export type StrategyDecisionTimelineItem = {
  kind: string;
  recorded_at: string;
  strategy_id: string;
  baseline_run_id?: string;
  challenger_run_id?: string;
  promotion_recommended: boolean;
  promotion_decision: StrategyPromotionDecision;
};

function readFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function readEvalQualityPassRate(report?: EvalRunReport): number | null {
  const quality = report?.quality;
  const qualityPassRate =
    quality && typeof quality === "object" && !Array.isArray(quality)
      ? readFiniteNumber(quality.pass_rate)
      : null;
  return qualityPassRate ?? readFiniteNumber(report?.success_rate);
}

export function readEvalDeliveryRate(report?: EvalRunReport): number | null {
  return readFiniteNumber(report?.delivery_rate) ?? readFiniteNumber(report?.success_rate);
}

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

export async function listStrategyDecisions(
  token: string
): Promise<{ items: StrategyDecisionTimelineItem[] }> {
  return requestJson<{ items: StrategyDecisionTimelineItem[] }>(
    "/api/profile/strategy-decisions",
    token,
    { method: "GET" }
  );
}
