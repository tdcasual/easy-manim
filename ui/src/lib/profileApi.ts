/**
 * 用户资料相关 API
 * 使用通用 requestJson 函数
 */
import { requestJson } from "./api";

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
  quality_passed_count?: number;
  failed_count: number;
  failed_count_recent: number;
  median_quality_score: number;
  top_issue_codes: Array<{ code: string; count: number }>;
  recent_profile_digests: string[];
};

export type ProfileSuggestionRationale = {
  confidence?: number;
  provenance?: Record<string, number>;
  supporting_evidence_counts?: Record<string, number>;
  field_support?: Record<
    string,
    {
      support_count?: number;
      source_type_counts?: Record<string, number>;
      distinct_session_count?: number;
      distinct_memory_count?: number;
      confidence?: number;
    }
  >;
  conflicts?: Array<{
    field: string;
    values?: Array<{ value: unknown; count: number }>;
  }>;
};

export type ProfileSuggestion = {
  suggestion_id: string;
  agent_id: string;
  patch: Record<string, unknown>;
  rationale: ProfileSuggestionRationale;
  status: string;
  created_at: string;
  applied_at?: string | null;
};

export type StrategyProfileSummary = {
  strategy_id: string;
  scope: string;
  prompt_cluster: string | null;
  status: string;
  routing_keywords: string[];
  params: Record<string, unknown>;
  guarded_rollout: Record<string, unknown>;
  last_eval_run: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export async function getProfile(token: string): Promise<AgentProfile> {
  return requestJson<AgentProfile>("/api/profile", token, { method: "GET" });
}

export async function getProfileScorecard(token: string): Promise<ProfileScorecard> {
  return requestJson<ProfileScorecard>("/api/profile/scorecard", token, { method: "GET" });
}

export async function listProfileSuggestions(token: string): Promise<{ items: ProfileSuggestion[] }> {
  return requestJson<{ items: ProfileSuggestion[] }>("/api/profile/suggestions", token, {
    method: "GET",
  });
}

export async function listProfileStrategies(token: string): Promise<{ items: StrategyProfileSummary[] }> {
  return requestJson<{ items: StrategyProfileSummary[] }>("/api/profile/strategies", token, {
    method: "GET",
  });
}

export async function applyProfilePatch(
  patch: Record<string, unknown>,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>("/api/profile/apply", token, {
    method: "POST",
    body: { patch },
  });
}
