/**
 * Toast context
 * Exported in a separate file to avoid react-refresh warnings.
 */
import { createContext } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastContextValue {
  toast: (message: string, type?: ToastType, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

export default ToastContext;
