/**
 * Toast hook
 * Uses the toast notification system.
 */
import { useContext } from "react";
import { ToastContext } from "./ToastContext";

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export default useToast;
