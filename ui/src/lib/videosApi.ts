/**
 * 视频相关 API
 * 使用通用 requestJson 函数
 */
import { requestJson } from "./api";

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
  return requestJson<RecentVideosResponse>(`/api/videos/recent?limit=${safeLimit}`, token, {
    method: "GET",
  });
}
