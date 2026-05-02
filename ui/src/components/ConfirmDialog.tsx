import { useRef } from "react";
import { AlertTriangle, X } from "lucide-react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useI18n } from "../app/locale";
import { Dialog, DialogOverlay } from "./ui/dialog";
import { cn } from "../lib/utils";

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

interface ConfirmDialogProps extends ConfirmOptions {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText,
  cancelText,
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useI18n();
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogPrimitive.Portal>
        <DialogOverlay
          role="button"
          aria-label="Dismiss confirm dialog backdrop"
          onClick={onCancel}
        />
        <DialogPrimitive.Content
          className={cn(
            "fixed left-[50%] top-[50%] z-50 grid w-full max-w-md translate-x-[-50%] translate-y-[-50%] gap-4 rounded-3xl border border-border bg-card p-0 shadow-2xl",
            "data-[state=open]:animate-pop-in data-[state=closed]:animate-fade-out",
            "focus:outline-none"
          )}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            confirmButtonRef.current?.focus();
          }}
        >
          <div className="flex flex-col p-5">
            <div className="flex flex-col items-center gap-4 text-center">
              <div
                className={cn(
                  "flex h-16 w-16 items-center justify-center rounded-full",
                  danger ? "bg-destructive/15 text-destructive" : "bg-peach-100 text-peach-600"
                )}
              >
                <AlertTriangle size={32} />
              </div>
              <div className="flex flex-col gap-1">
                <DialogPrimitive.Title className="text-xl font-semibold text-foreground">
                  {title}
                </DialogPrimitive.Title>
                <DialogPrimitive.Description className="text-sm text-muted-foreground">
                  {message}
                </DialogPrimitive.Description>
              </div>
            </div>
          </div>

          <div className="flex gap-3 border-t border-border p-5">
            <button
              type="button"
              className="flex-1 rounded-xl border border-border bg-muted px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted/80"
              onClick={onCancel}
            >
              {cancelText ?? t("common.cancel")}
            </button>
            <button
              ref={confirmButtonRef}
              type="button"
              className={cn(
                "flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform transition-shadow hover:-translate-y-0.5 hover:shadow-md",
                danger
                  ? "bg-destructive hover:bg-destructive/90"
                  : "bg-gradient-to-br from-pink-400 to-lavender-400"
              )}
              onClick={onConfirm}
            >
              {confirmText ?? t("common.confirm")}
            </button>
          </div>

          <DialogPrimitive.Close
            className="absolute right-4 top-4 inline-flex h-11 w-11 items-center justify-center rounded-full text-muted-foreground opacity-70 transition-opacity hover:bg-muted hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("common.close")}
          >
            <X className="h-4 w-4" />
            <span className="sr-only">{t("common.close")}</span>
          </DialogPrimitive.Close>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </Dialog>
  );
}

export default ConfirmDialog;
