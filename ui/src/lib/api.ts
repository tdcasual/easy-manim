type JsonObject = Record<string, unknown>;

export function apiBaseUrl(): string {
  // Prefer same-origin (Vite can proxy /api in dev).
  const base = import.meta.env?.VITE_API_BASE_URL;
  return typeof base === "string" ? base.replace(/\/+$/, "") : "";
}

export const ARTIFACT_PATHS = {
  video: (taskId: string) => `/api/tasks/${encodeURIComponent(taskId)}/artifacts/final_video.mp4`,
  script: (taskId: string) =>
    `/api/tasks/${encodeURIComponent(taskId)}/artifacts/current_script.py`,
  validationReport: (taskId: string) =>
    `/api/tasks/${encodeURIComponent(taskId)}/artifacts/validations/validation_report_v1.json`,
} as const;

export function resolveApiUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("/")) return `${apiBaseUrl()}${path}`;
  return `${apiBaseUrl()}/${path.replace(/^\/+/, "")}`;
}

async function readJson(response: Response): Promise<JsonObject> {
  const text = await response.text();
  if (!text) return {};
  try {
    const parsed = JSON.parse(text);
    return typeof parsed === "object" && parsed !== null ? (parsed as JsonObject) : {};
  } catch {
    return {};
  }
}

// ===== 通用 API 请求工具 =====

export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export interface RequestOptions extends Omit<RequestInit, "method" | "body"> {
  /** HTTP 方法 */
  method?: HttpMethod;
  /** 请求体（对象或字符串） */
  body?: unknown;
  /** 自定义 headers */
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: JsonObject
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * 通用 JSON 请求函数
 * 统一处理认证、错误和 JSON 解析
 *
 * @param path API 路径（以 / 开头）
 * @param token 认证令牌
 * @param options 请求选项
 * @returns 解析后的 JSON 数据
 */
export async function requestJson<T>(
  path: string,
  token: string | null,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers: customHeaders = {}, ...rest } = options;

  const headers = new Headers(customHeaders);
  headers.set("accept", "application/json");

  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

  const requestInit: RequestInit = {
    method,
    headers,
    ...rest,
  };

  if (body !== undefined) {
    if (typeof body === "string") {
      requestInit.body = body;
      headers.set("content-type", "application/json");
    } else {
      requestInit.body = JSON.stringify(body);
      headers.set("content-type", "application/json");
    }
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, requestInit);
  const text = await response.text().catch(() => "");

  if (!response.ok) {
    let payload: JsonObject = {};
    try {
      payload = JSON.parse(text);
    } catch {
      // 忽略解析错误
    }
    const detail =
      typeof payload.detail === "string" ? payload.detail : text || response.statusText;
    throw new ApiError(detail, response.status, payload);
  }

  if (!text) return {} as T;

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(`Invalid JSON response from ${path}`, 500);
  }
}

/**
 * 创建带认证的 API 客户端
 * @param getToken 获取 token 的函数
 * @returns API 方法集合
 */
export function createApiClient(getToken: () => string | null) {
  const token = () => getToken();

  return {
    get: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
      requestJson<T>(path, token(), { ...options, method: "GET" }),

    post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
      requestJson<T>(path, token(), { ...options, method: "POST", body }),

    put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
      requestJson<T>(path, token(), { ...options, method: "PUT", body }),

    patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
      requestJson<T>(path, token(), { ...options, method: "PATCH", body }),

    delete: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
      requestJson<T>(path, token(), { ...options, method: "DELETE" }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

export async function postSession(agentToken: string): Promise<{
  session_token: string;
  agent_id: string;
  name: string;
  expires_at: string;
}> {
  const response = await fetch(`${apiBaseUrl()}/api/sessions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ agent_token: agentToken }),
  });
  const payload = await readJson(response);
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "login_failed";
    throw new Error(detail);
  }
  return payload as { session_token: string; agent_id: string; name: string; expires_at: string };
}

export async function deleteCurrentSession(token: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/api/sessions/current`, {
    method: "DELETE",
    headers: {
      accept: "application/json",
      authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok && response.status !== 401) {
    const payload = await readJson(response);
    const detail = typeof payload.detail === "string" ? payload.detail : "logout_failed";
    throw new Error(detail);
  }
}
