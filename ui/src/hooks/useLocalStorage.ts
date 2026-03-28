/**
 * LocalStorage Hook
 * 安全地使用 localStorage，支持 SSR 环境
 */
import { useState, useEffect, useCallback } from "react";

export interface UseLocalStorageOptions<T> {
  /** 序列化函数 */
  serialize?: (value: T) => string;
  /** 反序列化函数 */
  deserialize?: (value: string) => T;
  /** 默认值 */
  defaultValue?: T;
}

/**
 * 安全地获取 localStorage 值
 */
function getStoredValue<T>(key: string, options: UseLocalStorageOptions<T>): T | null {
  const { deserialize = JSON.parse } = options;

  if (typeof window === "undefined") {
    return options.defaultValue ?? null;
  }

  try {
    const item = window.localStorage.getItem(key);
    if (item === null) {
      return options.defaultValue ?? null;
    }
    return deserialize(item);
  } catch (error) {
    console.warn(`Error reading localStorage key "${key}":`, error);
    return options.defaultValue ?? null;
  }
}

/**
 * LocalStorage Hook
 * 自动同步 localStorage 和 React 状态
 *
 * @param key localStorage 键名
 * @param options 配置选项
 * @returns [值, 设置函数, 删除函数]
 *
 * @example
 * ```tsx
 * const [theme, setTheme, removeTheme] = useLocalStorage<'light' | 'dark'>('theme', {
 *   defaultValue: 'light'
 * });
 *
 * // 使用
 * setTheme('dark');
 * removeTheme();
 * ```
 */
export function useLocalStorage<T>(
  key: string,
  options: UseLocalStorageOptions<T> = {}
): [T | null, (value: T | null) => void, () => void] {
  const { serialize = JSON.stringify } = options;

  const [storedValue, setStoredValue] = useState<T | null>(() => getStoredValue(key, options));

  // 监听其他标签页的变化
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === key && event.newValue !== null) {
        try {
          setStoredValue(getStoredValue(key, options));
        } catch (error) {
          console.warn(`Error parsing localStorage key "${key}":`, error);
        }
      } else if (event.key === key && event.newValue === null) {
        setStoredValue(options.defaultValue ?? null);
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [key, options]);

  const setValue = useCallback(
    (value: T | null) => {
      try {
        if (value === null) {
          window.localStorage.removeItem(key);
          setStoredValue(options.defaultValue ?? null);
        } else {
          const serialized = serialize(value);
          window.localStorage.setItem(key, serialized);
          setStoredValue(value);
        }
      } catch (error) {
        console.warn(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, serialize, options.defaultValue]
  );

  const removeValue = useCallback(() => {
    setValue(null);
  }, [setValue]);

  return [storedValue, setValue, removeValue];
}

export default useLocalStorage;
