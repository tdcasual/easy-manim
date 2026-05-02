/**
 * Async action execution hook
 * Auto-manages state and error boundaries.
 */
import { useState, useCallback, useRef } from "react";
import { AsyncStatus } from "./useAsyncStatus";

export interface UseAsyncActionOptions<TData, TError> {
  /** Success callback */
  onSuccess?: (data: TData) => void;
  /** Error callback */
  onError?: (error: TError) => void;
  /** Whether to auto-reset state */
  autoReset?: boolean;
  /** Auto-reset delay in milliseconds */
  autoResetDelay?: number;
}

export interface UseAsyncActionReturn<TData, TError> {
  /** Current status */
  status: AsyncStatus;
  /** Returned data */
  data: TData | null;
  /** Error message */
  error: TError | null;
  /** Whether the action is running */
  isLoading: boolean;
  /** Whether the action succeeded */
  isSuccess: boolean;
  /** Whether the action failed */
  isError: boolean;
  /** Execute the async action */
  execute: (...args: unknown[]) => Promise<TData | null>;
  /** Reset state */
  reset: () => void;
}

/**
 * Hook for executing async actions with full lifecycle management.
 *
 * @param action Async action function.
 * @param options Configuration options.
 * @returns State and controller.
 *
 * @example
 * ```tsx
 * const fetchUser = useAsyncAction(
 *   (id: string) => api.getUser(id),
 *   {
 *     onSuccess: (user) => console.log('Got user:', user),
 *     onError: (err) => console.error('Failed:', err),
 *   }
 * );
 *
 * // Execute
 * await fetchUser.execute('user-123');
 * ```
 */
export function useAsyncAction<TData = unknown, TError = Error>(
  action: (...args: unknown[]) => Promise<TData>,
  options: UseAsyncActionOptions<TData, TError> = {}
): UseAsyncActionReturn<TData, TError> {
  const { onSuccess, onError, autoReset = false, autoResetDelay = 3000 } = options;

  const [status, setStatus] = useState<AsyncStatus>("idle");
  const [data, setData] = useState<TData | null>(null);
  const [error, setError] = useState<TError | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setStatus("idle");
    setData(null);
    setError(null);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const execute = useCallback(
    async (...args: unknown[]): Promise<TData | null> => {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      setStatus("loading");
      setData(null);
      setError(null);

      try {
        const result = await action(...args);
        setData(result);
        setStatus("idle");
        onSuccess?.(result);

        if (autoReset) {
          setTimeout(() => reset(), autoResetDelay);
        }

        return result;
      } catch (err) {
        const typedError = (err instanceof Error ? err : new Error(String(err))) as TError;
        setError(typedError);
        setStatus("error");
        onError?.(typedError);
        return null;
      }
    },
    [action, onSuccess, onError, autoReset, autoResetDelay, reset]
  );

  return {
    status,
    data,
    error,
    isLoading: status === "loading",
    isSuccess: status === "idle" && data !== null,
    isError: status === "error",
    execute,
    reset,
  };
}

export default useAsyncAction;
