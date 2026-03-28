/**
 * Toast Hook
 * 使用 Toast 通知系统
 */
import { useContext } from "react";
import { ToastContext } from "./ToastContext";

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export default useToast;
