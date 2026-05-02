import { useCallback } from "react";
import { Toaster as SonnerToaster, toast as sonnerToast } from "sonner";
import { useTheme } from "../studio/hooks/useTheme";
import { ToastContext, ToastType } from "./ToastContext";

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const { isNight } = useTheme();

  const toast = useCallback((message: string, type: ToastType = "info", duration = 3000) => {
    const options = { duration };
    switch (type) {
      case "success":
        sonnerToast.success(message, options);
        break;
      case "error":
        sonnerToast.error(message, options);
        break;
      case "warning":
        sonnerToast.warning(message, options);
        break;
      default:
        sonnerToast(message, options);
    }
  }, []);

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
      <SonnerToaster
        position="top-center"
        richColors
        closeButton
        toastOptions={{
          classNames: {
            toast:
              "group toast flex w-full items-center gap-3 rounded-2xl border border-border bg-card p-4 shadow-lg",
            title: "text-sm font-medium text-foreground",
            description: "text-xs text-muted-foreground",
            actionButton:
              "inline-flex h-8 items-center justify-center rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground",
            cancelButton:
              "inline-flex h-8 items-center justify-center rounded-lg bg-muted px-3 text-xs font-medium text-muted-foreground",
            error: "border-destructive/30 text-destructive",
            success: "border-mint-500/30 text-mint-600",
            warning: "border-peach-500/30 text-peach-600",
            info: "border-sky-500/30 text-sky-600",
          },
        }}
        theme={isNight ? "dark" : "light"}
      />
    </ToastContext.Provider>
  );
}

export { ToastContext } from "./ToastContext";
export type { ToastType } from "./ToastContext";
