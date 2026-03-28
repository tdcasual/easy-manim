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
  failed_count: number;
  failed_count_recent: number;
  median_quality_score: number;
  top_issue_codes: string[];
  recent_profile_digests: string[];
};

export async function getProfile(token: string): Promise<AgentProfile> {
  return requestJson<AgentProfile>("/api/profile", token, { method: "GET" });
}

export async function getProfileScorecard(token: string): Promise<ProfileScorecard> {
  return requestJson<ProfileScorecard>("/api/profile/scorecard", token, { method: "GET" });
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
