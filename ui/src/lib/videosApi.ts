import { apiBaseUrl } from "./api";
import { clearSessionToken } from "./session";

async function requestJson<T>(path: string, token: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "GET",
    headers: {
      accept: "application/json",
      authorization: `Bearer ${token}`
    }
  });

  const text = await response.text().catch(() => "");
  if (!response.ok) {
    if (response.status === 401) clearSessionToken();
    throw new Error(`http_${response.status}:${text || response.statusText}`);
  }
  return (text ? JSON.parse(text) : {}) as T;
}

export type RecentVideoItem = {
  task_id: string;
  display_title?: string | null;
  title_source?: string | null;
  status: string;
  updated_at: string;
  latest_summary?: string | null;
  latest_video_url?: string | null;
  latest_preview_url?: string | null;
};

export type RecentVideosResponse = {
  items: RecentVideoItem[];
  next_cursor?: string | null;
};

export async function listRecentVideos(token: string, limit = 12): Promise<RecentVideosResponse> {
  const safeLimit = Math.max(1, Math.min(limit, 50));
  return requestJson<RecentVideosResponse>(`/api/videos/recent?limit=${safeLimit}`, token);
}
