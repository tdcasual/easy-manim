/**
 * useHistory - history management hook.
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { readLocale, translate } from "../../app/locale";
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

  if (diff < 60000) return translate(locale, "history.justNow");
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

  // Load history
  const loadHistory = useCallback(async () => {
    if (!sessionToken || isLoadingRef.current) return;

    // Cancel previous request
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

      // Component unmounted or request cancelled; skip state update
      if (controller.signal.aborted) return;

      setTasks(tasksRes.items || []);
      setVideos(videosRes.items || []);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      // loading failures are handled by the UI layer
    } finally {
      // Update state only if this is the current active request
      if (abortControllerRef.current === controller) {
        isLoadingRef.current = false;
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [sessionToken]);

  // Cancel request on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Prepare history data
  const historyItems: HistoryItem[] = tasks.map((task) => {
    const video = videos.find((v) => v.task_id === task.task_id);
    const timestamp = video?.updated_at ? formatTime(new Date(video.updated_at)) : "just now";

    return {
      id: task.task_id,
      title: task.display_title ?? task.task_id,
      status: task.status.toLowerCase() as HistoryItem["status"],
      timestamp,
      thumbnailUrl: video?.latest_preview_url,
      videoUrl: video?.latest_video_url,
    };
  });

  // Get most recent completed task
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
