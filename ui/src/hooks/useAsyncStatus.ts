/**
 * Async status management hook
 * Unifies loading/error/idle state to remove duplication.
 */
import { useState, useCallback } from "react";

export type AsyncStatus = "idle" | "loading" | "error";

export interface UseAsyncStatusReturn {
  /** Current status */
  status: AsyncStatus;
  /** Error message */
  error: string | null;
  /** Whether loading */
  isLoading: boolean;
  /** Whether an error occurred */
  isError: boolean;
  /** Whether idle */
  isIdle: boolean;
  /** Start loading */
  startLoading: () => void;
  /** Set error state */
  setErrorState: (error: string | Error | unknown) => void;
  /** Reset to idle */
  reset: () => void;
  /** Mark as succeeded */
  succeed: () => void;
}

/**
 * Hook that manages async operation status.
 * @param initialStatus Initial status, defaults to "idle".
 * @returns State and controls.
 *
 * @example
 * ```tsx
 * const { status, error, isLoading, startLoading, setErrorState, reset } = useAsyncStatus();
 *
 * async function handleSubmit() {
 *   startLoading();
 *   try {
 *     await api.submit(data);
 *     reset();
 *   } catch (err) {
 *     setErrorState(err);
 *   }
 * }
 * ```
 */
export function useAsyncStatus(initialStatus: AsyncStatus = "idle"): UseAsyncStatusReturn {
  const [status, setStatus] = useState<AsyncStatus>(initialStatus);
  const [error, setError] = useState<string | null>(null);

  const startLoading = useCallback(() => {
    setStatus("loading");
    setError(null);
  }, []);

  const setErrorState = useCallback((err: string | Error | unknown) => {
    setStatus("error");
    if (typeof err === "string") {
      setError(err);
    } else if (err instanceof Error) {
      setError(err.message);
    } else {
      setError(String(err) || "Unknown error");
    }
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setError(null);
  }, []);

  const succeed = useCallback(() => {
    setStatus("idle");
    setError(null);
  }, []);

  return {
    status,
    error,
    isLoading: status === "loading",
    isError: status === "error",
    isIdle: status === "idle",
    startLoading,
    setErrorState,
    reset,
    succeed,
  };
}

export default useAsyncStatus;
