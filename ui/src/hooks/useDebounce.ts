/**
 * 防抖 Hook
 * 用于处理高频触发的事件（搜索输入、窗口调整等）
 */
import { useState, useEffect, useRef, useCallback } from "react";

/**
 * 防抖值 Hook
 * 延迟更新值，减少不必要的渲染或请求
 *
 * @param value 原始值
 * @param delay 延迟时间（毫秒）
 * @returns 防抖后的值
 *
 * @example
 * ```tsx
 * const [searchTerm, setSearchTerm] = useState('');
 * const debouncedSearch = useDebounce(searchTerm, 300);
 *
 * // 只在停止输入 300ms 后触发
 * useEffect(() => {
 *   performSearch(debouncedSearch);
 * }, [debouncedSearch]);
 * ```
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * 防抖回调 Hook
 * 返回一个防抖的函数
 *
 * @param callback 回调函数
 * @param delay 延迟时间（毫秒）
 * @returns 防抖后的回调函数
 *
 * @example
 * ```tsx
 * const debouncedSave = useDebouncedCallback(
 *   (data) => api.save(data),
 *   500
 * );
 *
 * // 频繁调用不会立即执行
 * debouncedSave(newData);
 * ```
 */
export function useDebouncedCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);

  // 保持回调引用最新
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    },
    [delay]
  );
}

/**
 * 节流 Hook
 * 限制函数执行频率
 *
 * @param callback 回调函数
 * @param limit 限制时间（毫秒）
 * @returns 节流后的回调函数
 */
export function useThrottle<T extends (...args: unknown[]) => unknown>(
  callback: T,
  limit: number
): (...args: Parameters<T>) => void {
  const lastRunRef = useRef<number>(0);
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  return useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now();
      if (now - lastRunRef.current >= limit) {
        lastRunRef.current = now;
        callbackRef.current(...args);
      }
    },
    [limit]
  );
}

export default useDebounce;
