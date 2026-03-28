/**
 * Toast Notification System
 * 全局通知系统
 */
import { useState, useCallback, useEffect } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";
import { ToastContext, ToastType } from "./ToastContext";
import "./Toast.css";

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, type: ToastType = "info", duration = 3000) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev, { id, message, type, duration }]);
      setTimeout(() => removeToast(id), duration);
    },
    [removeToast]
  );

  const success = useCallback(
    (message: string, duration?: number) => {
      toast(message, "success", duration);
    },
    [toast]
  );

  const error = useCallback(
    (message: string, duration?: number) => {
      toast(message, "error", duration);
    },
    [toast]
  );

  const warning = useCallback(
    (message: string, duration?: number) => {
      toast(message, "warning", duration);
    },
    [toast]
  );

  const info = useCallback(
    (message: string, duration?: number) => {
      toast(message, "info", duration);
    },
    [toast]
  );

  return (
    <ToastContext.Provider value={{ toast, success, error, warning, info }}>
      {children}
      <div className="toast-container" role="region" aria-label="通知">
        {toasts.map((t) => (
          <Toast key={t.id} item={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function Toast({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, item.duration);
    return () => clearTimeout(timer);
  }, [item.duration, onClose]);

  const icons = {
    success: <CheckCircle size={18} />,
    error: <AlertCircle size={18} />,
    warning: <AlertCircle size={18} />,
    info: <Info size={18} />,
  };

  const labels = {
    success: "成功",
    error: "错误",
    warning: "警告",
    info: "提示",
  };

  return (
    <div className={`toast toast-${item.type}`} role="alert" aria-live="polite">
      <span className="toast-icon" aria-label={labels[item.type]}>
        {icons[item.type]}
      </span>
      <span className="toast-message">{item.message}</span>
      <button className="toast-close" onClick={onClose} aria-label="关闭通知" type="button">
        <X size={14} />
      </button>
    </div>
  );
}

export default ToastProvider;
export { ToastContext } from "./ToastContext";
export type { ToastType } from "./ToastContext";
