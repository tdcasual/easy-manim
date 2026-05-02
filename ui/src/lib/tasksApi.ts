/**
 * Task-related API
 * Uses the generic requestJson helper.
 */
import { requestJson } from "./api";

export type TaskSnapshot = {
  task_id: string;
  thread_id?: string | null;
  iteration_id?: string | null;
  display_title?: string | null;
  title_source?: string | null;
  status: string;
  phase: string;
  attempt_count?: number;
  delivery_status?: string | null;
  resolved_task_id?: string | null;
  completion_mode?: string | null;
  delivery_tier?: string | null;
  delivery_stop_reason?: string | null;
  latest_validation_summary?: { summary?: string };
  artifact_summary?: Record<string, unknown>;
};

export type TaskResult = {
  task_id: string;
  status: string;
  ready: boolean;
  delivery_status?: string | null;
  resolved_task_id?: string | null;
  completion_mode?: string | null;
  delivery_tier?: string | null;
  delivery_stop_reason?: string | null;
  summary?: string | null;
  video_resource?: string | null;
  video_download_url?: string | null;
  script_download_url?: string | null;
  validation_report_download_url?: string | null;
  preview_download_urls?: string[] | null;
};

export type TaskListItem = {
  task_id: string;
  status: string;
  display_title?: string | null;
  title_source?: string | null;
};

export type TaskListResponse = { items: TaskListItem[] };

export const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export type CreateTaskResponse = {
  task_id: string;
  display_title?: string | null;
  title_source?: string | null;
};

export type WorkflowReviewPanelTone = "ready" | "attention" | "blocked";
export type WorkflowReviewDisplayPriority = "normal" | "high";
export type WorkflowReviewSectionId = "recommended" | "available" | "blocked";
export type WorkflowReviewActionFamily = "review_decision" | "workflow_memory" | "combined";
export type WorkflowReviewDecisionKind = "accept" | "revise" | "retry" | "repair" | "escalate";

export type WorkflowReviewActionMemoryChange = {
  pin_memory_ids: string[];
  unpin_memory_ids: string[];
  pin_count: number;
  unpin_count: number;
};

export type WorkflowReviewActionIntent = {
  review_decision?: WorkflowReviewDecisionKind | null;
  mutates_workflow_memory: boolean;
  workflow_memory_change?: WorkflowReviewActionMemoryChange | null;
};

export type WorkflowReviewActionCard = {
  action_id: string;
  title: string;
  button_label: string;
  action_family: WorkflowReviewActionFamily;
  summary: string;
  blocked: boolean;
  reasons: string[];
  is_primary: boolean;
  intent: WorkflowReviewActionIntent;
  payload: Record<string, unknown>;
};

export type WorkflowReviewActionSection = {
  section_id: WorkflowReviewSectionId;
  title: string;
  summary: string;
  items: WorkflowReviewActionCard[];
};

export type WorkflowReviewPanelBadge = {
  badge_id: string;
  label: string;
  value: string;
  tone: "neutral" | "ready" | "attention" | "blocked";
};

export type WorkflowReviewPanelEvent = {
  event_type: string;
  title: string;
  summary: string;
  memory_id?: string | null;
  created_at: string;
};

export type WorkflowAppliedActionFeedback = {
  event_type: string;
  tone: "info" | "success";
  title: string;
  summary: string;
  memory_id?: string | null;
  created_at: string;
  follow_up_action_id?: string | null;
};

export type WorkflowReviewStatusSummary = {
  recommended_action_id?: string | null;
  acceptance_ready: boolean;
  acceptance_blockers: string[];
  pinned_memory_count: number;
  pending_memory_recommendation_count: number;
  has_pending_memory_updates: boolean;
  latest_workflow_memory_event_type?: string | null;
  latest_workflow_memory_event_at?: string | null;
};

export type WorkflowReviewRenderContract = {
  badge_order: string[];
  panel_tone: WorkflowReviewPanelTone;
  display_priority: WorkflowReviewDisplayPriority;
  section_order: WorkflowReviewSectionId[];
  default_focus_section_id?: WorkflowReviewSectionId | null;
  default_expanded_section_ids: WorkflowReviewSectionId[];
  section_presentations: Array<{
    section_id: WorkflowReviewSectionId;
    tone: "accent" | "neutral" | "muted";
    collapsible: boolean;
  }>;
  sticky_primary_action_id?: string | null;
  sticky_primary_action_emphasis: "normal" | "strong";
  applied_feedback_dismissible: boolean;
};

export type WorkflowReviewControls = {
  action_sections?: { items: WorkflowReviewActionSection[] } | null;
  panel_header?: {
    title?: string;
    tone: WorkflowReviewPanelTone;
    summary: string;
    badges: WorkflowReviewPanelBadge[];
    highlighted_event?: WorkflowReviewPanelEvent | null;
  } | null;
  applied_action_feedback?: WorkflowAppliedActionFeedback | null;
  status_summary?: WorkflowReviewStatusSummary | null;
  render_contract?: WorkflowReviewRenderContract | null;
};

export type VideoProcessTimelineItem = {
  item_id: string;
  kind: "task_event" | "agent_run" | "system";
  title: string;
  summary: string;
  created_at: string;
  role?: string | null;
  task_id?: string | null;
  status?: string | null;
};

export type ReviewBundle = {
  task_id: string;
  status: string;
  phase: string;
  workflow_review_controls?: WorkflowReviewControls | null;
};

export type ApplyReviewDecisionRequest = {
  review_decision: {
    decision: WorkflowReviewDecisionKind;
    summary: string;
    feedback?: string | null;
    preserve_working_parts?: boolean;
    decision_role?: string | null;
    confidence?: number;
    issues?: Array<Record<string, unknown>>;
    stop_reason?: string | null;
    collaboration?: Record<string, unknown> | null;
  };
  memory_ids?: string[] | null;
  pin_workflow_memory_ids?: string[] | null;
  unpin_workflow_memory_ids?: string[] | null;
};

export type ApplyReviewDecisionResponse = {
  task_id: string;
  root_task_id?: string | null;
  action: string;
  created_task_id?: string | null;
  reason: string;
  refresh_scope?: "panel_only" | "task_and_panel" | "navigate";
  refresh_task_id?: string | null;
  workflow_memory_state?: {
    root_task_id: string;
    pinned_memory_ids: string[];
    persistent_memory_context_summary?: string | null;
    persistent_memory_context_digest?: string | null;
  } | null;
};

export type CreateTaskParams = {
  prompt: string;
  resolution?: string;
  duration?: string;
  style?: string;
  quality?: string;
};

export async function listTasks(token: string): Promise<TaskListResponse> {
  return requestJson<TaskListResponse>("/api/tasks", token, { method: "GET" });
}

export async function createTask(
  params: CreateTaskParams | string,
  token: string
): Promise<CreateTaskResponse> {
  const body = typeof params === "string" ? { prompt: params } : params;
  return requestJson<CreateTaskResponse>("/api/tasks", token, {
    method: "POST",
    body,
  });
}

export async function getTask(taskId: string, token: string): Promise<TaskSnapshot> {
  return requestJson<TaskSnapshot>(`/api/tasks/${encodeURIComponent(taskId)}`, token, {
    method: "GET",
  });
}

export async function getTaskResult(taskId: string, token: string): Promise<TaskResult> {
  return requestJson<TaskResult>(`/api/tasks/${encodeURIComponent(taskId)}/result`, token, {
    method: "GET",
  });
}

export async function getReviewBundle(taskId: string, token: string): Promise<ReviewBundle> {
  return requestJson<ReviewBundle>(
    `/api/tasks/${encodeURIComponent(taskId)}/review-bundle`,
    token,
    {
      method: "GET",
    }
  );
}

export async function applyReviewDecision(
  taskId: string,
  payload: ApplyReviewDecisionRequest,
  token: string
): Promise<ApplyReviewDecisionResponse> {
  return requestJson<ApplyReviewDecisionResponse>(
    `/api/tasks/${encodeURIComponent(taskId)}/review-decision`,
    token,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function reviseTask(
  taskId: string,
  feedback: string,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/tasks/${encodeURIComponent(taskId)}/revise`,
    token,
    { method: "POST", body: { feedback } }
  );
}

export async function retryTask(taskId: string, token: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/tasks/${encodeURIComponent(taskId)}/retry`,
    token,
    { method: "POST" }
  );
}

export async function cancelTask(
  taskId: string,
  token: string
): Promise<{ task_id: string; status: string }> {
  return requestJson<{ task_id: string; status: string }>(
    `/api/tasks/${encodeURIComponent(taskId)}/cancel`,
    token,
    { method: "POST" }
  );
}
