import { useEffect, useState } from "react";

import { getTaskResult, type TaskResult } from "../../lib/tasksApi";

type TaskArtifactDownloadsState = {
  downloads: TaskResult | null;
  loading: boolean;
  error: string | null;
};

export function useTaskArtifactDownloads(
  taskId: string | null,
  token: string | null
): TaskArtifactDownloadsState {
  const [downloads, setDownloads] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId || !token) {
      setDownloads(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getTaskResult(taskId, token)
      .then((result) => {
        if (!cancelled) {
          setDownloads(result);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDownloads(null);
          setError(err instanceof Error ? err.message : "Failed to load task artifact downloads");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [taskId, token]);

  return { downloads, loading, error };
}
