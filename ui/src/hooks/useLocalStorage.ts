/**
 * LocalStorage hook
 * Safely uses localStorage with SSR support.
 */
import { useState, useEffect, useCallback } from "react";

export interface UseLocalStorageOptions<T> {
  /** Serialize function */
  serialize?: (value: T) => string;
  /** Deserialize function */
  deserialize?: (value: string) => T;
  /** Default value */
  defaultValue?: T;
}

/**
 * Safely retrieve a localStorage value.
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
 * LocalStorage hook
 * Automatically syncs localStorage and React state.
 *
 * @param key localStorage key.
 * @param options Configuration options.
 * @returns [value, setValue, removeValue]
 *
 * @example
 * ```tsx
 * const [theme, setTheme, removeTheme] = useLocalStorage<'light' | 'dark'>('theme', {
 *   defaultValue: 'light'
 * });
 *
 * // Usage
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

  // Listen for changes from other tabs
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
