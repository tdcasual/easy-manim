/**
 * 异步动作执行 Hook
 * 自动处理状态管理和错误边界
 */
import { useState, useCallback, useRef } from "react";
import { AsyncStatus } from "./useAsyncStatus";

export interface UseAsyncActionOptions<TData, TError> {
  /** 成功回调 */
  onSuccess?: (data: TData) => void;
  /** 错误回调 */
  onError?: (error: TError) => void;
  /** 是否自动重置状态 */
  autoReset?: boolean;
  /** 自动重置延迟（毫秒） */
  autoResetDelay?: number;
}

export interface UseAsyncActionReturn<TData, TError> {
  /** 当前状态 */
  status: AsyncStatus;
  /** 返回数据 */
  data: TData | null;
  /** 错误信息 */
  error: TError | null;
  /** 是否正在执行 */
  isLoading: boolean;
  /** 是否成功 */
  isSuccess: boolean;
  /** 是否失败 */
  isError: boolean;
  /** 执行异步动作 */
  execute: (...args: unknown[]) => Promise<TData | null>;
  /** 重置状态 */
  reset: () => void;
}

/**
 * 用于执行异步动作的 Hook，自动管理完整生命周期
 *
 * @param action 异步动作函数
 * @param options 配置选项
 * @returns 状态和控制器
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
 * // 执行
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
      // 取消之前的请求
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
