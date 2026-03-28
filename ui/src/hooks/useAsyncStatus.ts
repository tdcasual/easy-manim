/**
 * 异步操作状态管理 Hook
 * 统一处理 loading/error/idle 状态，消除重复代码
 */
import { useState, useCallback } from "react";

export type AsyncStatus = "idle" | "loading" | "error";

export interface UseAsyncStatusReturn {
  /** 当前状态 */
  status: AsyncStatus;
  /** 错误信息 */
  error: string | null;
  /** 是否处于加载中 */
  isLoading: boolean;
  /** 是否发生错误 */
  isError: boolean;
  /** 是否处于空闲状态 */
  isIdle: boolean;
  /** 开始加载 */
  startLoading: () => void;
  /** 设置错误状态 */
  setErrorState: (error: string | Error | unknown) => void;
  /** 重置为空闲状态 */
  reset: () => void;
  /** 成功完成 */
  succeed: () => void;
}

/**
 * 管理异步操作状态的 Hook
 * @param initialStatus 初始状态，默认为 "idle"
 * @returns 状态和控制函数
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
