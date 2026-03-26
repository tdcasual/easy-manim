import { clearSessionToken } from "./session";
import { apiBaseUrl } from "./api";

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

export async function listTasks(token: string): Promise<TaskListResponse> {
  return requestJson<TaskListResponse>("/api/tasks", { method: "GET" }, token);
}

export async function createTask(prompt: string, token: string): Promise<CreateTaskResponse> {
  return requestJson<CreateTaskResponse>(
    "/api/tasks",
    { method: "POST", body: JSON.stringify({ prompt }) },
    token
  );
}

export async function getTask(taskId: string, token: string): Promise<TaskSnapshot> {
  return requestJson<TaskSnapshot>(`/api/tasks/${encodeURIComponent(taskId)}`, { method: "GET" }, token);
}

export async function getTaskResult(taskId: string, token: string): Promise<TaskResult> {
  return requestJson<TaskResult>(`/api/tasks/${encodeURIComponent(taskId)}/result`, { method: "GET" }, token);
}

export async function reviseTask(taskId: string, feedback: string, token: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/tasks/${encodeURIComponent(taskId)}/revise`,
    { method: "POST", body: JSON.stringify({ feedback }) },
    token
  );
}

export async function retryTask(taskId: string, token: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/tasks/${encodeURIComponent(taskId)}/retry`,
    { method: "POST" },
    token
  );
}

export async function cancelTask(taskId: string, token: string): Promise<{ task_id: string; status: string }> {
  return requestJson<{ task_id: string; status: string }>(
    `/api/tasks/${encodeURIComponent(taskId)}/cancel`,
    { method: "POST" },
    token
  );
}
