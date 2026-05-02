/**
 * useTaskManager - task management hook.
 * Handles core logic for creation, polling, and cancellation.
 */
import { useCallback, useRef, useEffect } from "react";
import { createTask, getTask, getTaskResult, cancelTask } from "../../lib/tasksApi";
import { readLocale, translate } from "../../app/locale";
import { useStudioStore } from "../store";
import type { TaskError } from "../store";

function parseError(err: unknown): TaskError {
  const message = err instanceof Error ? err.message : String(err);
  const locale = readLocale();
  const t = (key: string) => translate(locale, key);

  if (
    message.includes("fetch") ||
    message.includes("network") ||
    message.includes("Failed to fetch")
  ) {
    return { type: "network", message: t("studio.error.network"), retryable: true };
  }

  if (message.includes("timeout") || message.includes("ETIMEDOUT")) {
    return { type: "timeout", message: t("studio.error.timeout"), retryable: true };
  }

  if (message.includes("http_")) {
    const statusCode = message.match(/http_(\d+)/)?.[1];
    if (statusCode === "429") {
      return { type: "generation", message: t("studio.error.rateLimit"), retryable: true };
    }
    if (statusCode === "500" || statusCode === "502" || statusCode === "503") {
      return { type: "generation", message: t("studio.error.serverError"), retryable: true };
    }
    if (statusCode === "401" || statusCode === "403") {
      return { type: "unknown", message: t("studio.error.unauthorized"), retryable: false };
    }
  }

  return { type: "unknown", message: message || t("studio.error.unknown"), retryable: true };
}

interface UseTaskManagerOptions {
  sessionToken: string | null;
  onTaskComplete?: () => void;
}

export function useTaskManager({ sessionToken, onTaskComplete }: UseTaskManagerOptions) {
  // Use selectors to fetch only needed actions, avoiding full-store dependencies
  const setIsGenerating = useStudioStore((state) => state.setIsGenerating);
  const setCurrentTask = useStudioStore((state) => state.setCurrentTask);
  const setError = useStudioStore((state) => state.setError);
  const updateTaskStatus = useStudioStore((state) => state.updateTaskStatus);
  const currentTask = useStudioStore((state) => state.currentTask);

  const pollCleanupRef = useRef<(() => void) | null>(null);
  const submitLockRef = useRef(false);

  // Clean up polling
  const cleanupPolling = useCallback(() => {
    if (pollCleanupRef.current) {
      pollCleanupRef.current();
      pollCleanupRef.current = null;
    }
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => cleanupPolling();
  }, [cleanupPolling]);

  // Submit task
  const submitTask = useCallback(
    async (params: {
      prompt: string;
      resolution?: string;
      duration?: string;
      style?: string;
      quality?: string;
    }) => {
      if (!sessionToken || submitLockRef.current) {
        return { success: false, error: "Unable to submit" };
      }

      submitLockRef.current = true;
      setIsGenerating(true);

      try {
        const result = await createTask(params, sessionToken);

        if (result?.task_id) {
          setCurrentTask({
            id: result.task_id,
            title: result.display_title ?? params.prompt,
            status: "queued",
          });
          return { success: true, taskId: result.task_id };
        }

        return { success: false, error: "Failed to create task" };
      } catch (err) {
        const parsedError = parseError(err);
        setError(parsedError);
        setIsGenerating(false);
        return { success: false, error: parsedError.message };
      } finally {
        submitLockRef.current = false;
      }
    },
    [sessionToken, setIsGenerating, setCurrentTask, setError]
  );

  // Start polling task status
  const startPolling = useCallback(
    (taskId: string) => {
      if (!sessionToken) return;

      cleanupPolling();

      let timeoutId: number | null = null;
      let isCancelled = false;
      let errorAttempt = 0;

      const getPollInterval = (status: string, hasError: boolean) => {
        if (hasError) {
          return Math.min(30000, 1000 * Math.pow(2, errorAttempt));
        }
        if (status === "queued") return 5000;
        if (status === "running") return 3000;
        return 3000;
      };

      const checkStatus = async () => {
        if (isCancelled || !sessionToken) return;

        try {
          const [task, result] = await Promise.all([
            getTask(taskId, sessionToken),
            getTaskResult(taskId, sessionToken),
          ]);

          if (isCancelled) return;

          errorAttempt = 0;

          if (task.status === "completed") {
            updateTaskStatus("completed", result.video_download_url ?? undefined);
            setIsGenerating(false);
            onTaskComplete?.();
          } else if (["running", "queued"].includes(task.status)) {
            updateTaskStatus(task.status as "running" | "queued");
            const interval = getPollInterval(task.status, false);
            timeoutId = window.setTimeout(checkStatus, interval);
          } else if (task.status === "failed") {
            setError({ type: "generation", message: "Task execution failed", retryable: true });
            setIsGenerating(false);
          }
        } catch (err) {
          if (!isCancelled) {
            errorAttempt++;
            const interval = getPollInterval("unknown", true);
            timeoutId = window.setTimeout(checkStatus, interval);

            if (errorAttempt >= 3) {
              setError(parseError(err));
              setIsGenerating(false);
            }
          }
        }
      };

      timeoutId = window.setTimeout(checkStatus, 1000);

      pollCleanupRef.current = () => {
        isCancelled = true;
        if (timeoutId !== null) clearTimeout(timeoutId);
      };
    },
    [sessionToken, cleanupPolling, onTaskComplete, updateTaskStatus, setIsGenerating, setError]
  );

  // Cancel task
  const cancelCurrentTask = useCallback(async () => {
    if (!sessionToken || !currentTask?.id) return { success: false };

    try {
      cleanupPolling();
      await cancelTask(currentTask.id, sessionToken);
      setIsGenerating(false);
      updateTaskStatus("cancelled");
      return { success: true };
    } catch {
      cleanupPolling();
      setIsGenerating(false);
      return { success: false };
    }
  }, [sessionToken, currentTask, cleanupPolling, setIsGenerating, updateTaskStatus]);

  return {
    submitTask,
    startPolling,
    cancelCurrentTask,
  };
}
