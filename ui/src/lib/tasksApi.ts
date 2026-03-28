/**
 * 任务相关 API
 * 使用通用 requestJson 函数
 */
import { requestJson } from "./api";

export type TaskSnapshot = {
  task_id: string;
  display_title?: string | null;
  title_source?: string | null;
  status: string;
  phase: string;
  attempt_count?: number;
  latest_validation_summary?: { summary?: string };
  artifact_summary?: Record<string, unknown>;
};

export type TaskResult = {
  task_id: string;
  status: string;
  ready: boolean;
  summary?: string | null;
  video_resource?: string | null;
  video_download_url?: string | null;
  preview_download_urls?: string[] | null;
};

export type TaskListItem = {
  task_id: string;
  status: string;
  display_title?: string | null;
  title_source?: string | null;
};

export type TaskListResponse = { items: TaskListItem[] };

export type CreateTaskResponse = {
  task_id: string;
  display_title?: string | null;
  title_source?: string | null;
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
