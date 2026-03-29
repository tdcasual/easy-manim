/**
 * useHistory - 历史记录管理 Hook
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { readLocale } from "../../app/locale";
import { listTasks, TaskListItem } from "../../lib/tasksApi";
import { listRecentVideos, RecentVideoItem } from "../../lib/videosApi";

export interface HistoryItem {
  id: string;
  title: string;
  status: "completed" | "running" | "rendering" | "queued" | "failed" | "cancelled";
  timestamp: string;
  thumbnailUrl?: string | null;
  videoUrl?: string | null;
}

function formatTime(date: Date): string {
  const locale = readLocale();
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });

  if (diff < 60000) return locale === "zh-CN" ? "刚刚" : "just now";
  if (diff < 3600000) return formatter.format(-Math.floor(diff / 60000), "minute");
  if (diff < 86400000) return formatter.format(-Math.floor(diff / 3600000), "hour");
  return formatter.format(-Math.floor(diff / 86400000), "day");
}

interface UseHistoryOptions {
  sessionToken: string | null;
}

export function useHistory({ sessionToken }: UseHistoryOptions) {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [videos, setVideos] = useState<RecentVideoItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const isLoadingRef = useRef(false);

  // 加载历史
  const loadHistory = useCallback(async () => {
    if (!sessionToken || isLoadingRef.current) return;

    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    isLoadingRef.current = true;
    setIsLoading(true);

    try {
      const [tasksRes, videosRes] = await Promise.all([
        listTasks(sessionToken),
        listRecentVideos(sessionToken, 20),
      ]);

      // 组件已卸载或请求已取消，不更新状态
      if (controller.signal.aborted) return;

      setTasks(tasksRes.items || []);
      setVideos(videosRes.items || []);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      console.error("Failed to load history:", err);
    } finally {
      // 只有当这是当前活动的请求时才更新状态
      if (abortControllerRef.current === controller) {
        isLoadingRef.current = false;
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [sessionToken]);

  // 组件卸载时取消请求
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // 准备历史数据
  const historyItems: HistoryItem[] = tasks.map((task) => {
    const video = videos.find((v) => v.task_id === task.task_id);
    const timestamp = video?.updated_at ? formatTime(new Date(video.updated_at)) : "刚刚";

    return {
      id: task.task_id,
      title: task.display_title ?? task.task_id,
      status: task.status.toLowerCase() as HistoryItem["status"],
      timestamp,
      thumbnailUrl: video?.latest_preview_url,
      videoUrl: video?.latest_video_url,
    };
  });

  // 获取最近完成的任务
  const getRecentCompleted = useCallback(() => {
    return videos.find((v) => v.status.toLowerCase() === "completed");
  }, [videos]);

  return {
    historyItems,
    isLoading,
    loadHistory,
    getRecentCompleted,
  };
}
