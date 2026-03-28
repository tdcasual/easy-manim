/**
 * Toast Context
 * 单独文件导出以避免 react-refresh 警告
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
