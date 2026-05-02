/**
 * Shared hooks library
 * Collection of reusable React hooks.
 */

// Async state management
export { useAsyncStatus, type AsyncStatus, type UseAsyncStatusReturn } from "./useAsyncStatus";
export {
  useAsyncAction,
  type UseAsyncActionOptions,
  type UseAsyncActionReturn,
} from "./useAsyncAction";

// Input handling
export { useDebounce, useDebouncedCallback, useThrottle } from "./useDebounce";

// Storage
export { useLocalStorage, type UseLocalStorageOptions } from "./useLocalStorage";
