import { requestJson } from "./api";

export type RuntimeFeatureStatus = {
  checked: boolean;
  available: boolean;
  missing_checks: string[];
  smoke_error?: string | null;
};

export type RuntimeCapabilityStatus = {
  rollout_profile: string;
  effective: Record<string, boolean>;
};

export type RuntimeStatus = {
  provider: {
    mode: string;
    configured: boolean;
    api_base_present: boolean;
  };
  worker: {
    embedded: boolean;
    workers: Array<{
      worker_id: string;
      identity: string;
      last_seen_at: string;
      stale: boolean;
    }>;
  };
  capabilities: RuntimeCapabilityStatus;
  autonomy_guard: {
    enabled: boolean;
    allowed: boolean;
    reasons: string[];
    canary_available: boolean;
    canary_delivered?: boolean | null;
    delivery_rate: number;
    min_delivery_rate: number;
    emergency_fallback_rate: number;
    max_emergency_fallback_rate: number;
    branch_rejection_rate: number;
    max_branch_rejection_rate: number;
  };
  delivery_summary?: {
    total_roots: number;
    delivered_roots: number;
    failed_roots: number;
    pending_roots: number;
    delivery_rate: number;
    emergency_fallback_rate: number;
    case_status_counts: Record<string, number>;
    agent_run_status_counts: Record<string, number>;
    agent_run_role_status_counts: Record<string, Record<string, number>>;
    agent_run_stop_reason_counts: Record<string, number>;
    completion_modes: Record<string, number>;
    challenger_branches_completed: number;
    challenger_branches_rejected: number;
    branch_rejection_rate: number;
    arbitration_attempts: number;
    arbitration_successes: number;
    arbitration_success_rate: number;
    repair_loop_saturation_count: number;
    repair_loop_saturation_rate: number;
    top_stop_reasons: Array<{
      reason: string;
      count: number;
    }>;
  };
  features: Record<string, RuntimeFeatureStatus>;
};

export async function getRuntimeStatus(token: string): Promise<RuntimeStatus> {
  return requestJson<RuntimeStatus>("/api/runtime/status", token, { method: "GET" });
}
