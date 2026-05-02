/**
 * Debounce hook
 * For high-frequency events like search input or window resize.
 */
import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Debounced value hook
 * Delays value updates to reduce unnecessary renders or requests.
 *
 * @param value Original value.
 * @param delay Delay in milliseconds.
 * @returns Debounced value.
 *
 * @example
 * ```tsx
 * const [searchTerm, setSearchTerm] = useState('');
 * const debouncedSearch = useDebounce(searchTerm, 300);
 *
 * // Triggers only 300ms after typing stops.
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
 * Debounced callback hook
 * Returns a debounced function.
 *
 * @param callback Callback function.
 * @param delay Delay in milliseconds.
 * @returns Debounced callback.
 *
 * @example
 * ```tsx
 * const debouncedSave = useDebouncedCallback(
 *   (data) => api.save(data),
 *   500
 * );
 *
 * // Frequent calls are not executed immediately.
 * debouncedSave(newData);
 * ```
 */
export function useDebouncedCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);

  // Keep callback reference up to date
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
 * Throttle hook
 * Limits function execution frequency.
 *
 * @param callback Callback function.
 * @param limit Throttle window in milliseconds.
 * @returns Throttled callback.
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
