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
  features: Record<string, RuntimeFeatureStatus>;
};

export async function getRuntimeStatus(token: string): Promise<RuntimeStatus> {
  return requestJson<RuntimeStatus>("/api/runtime/status", token, { method: "GET" });
}
