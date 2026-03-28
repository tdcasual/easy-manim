/**
 * Shared Hooks Library
 * 可复用的 React Hooks 集合
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
