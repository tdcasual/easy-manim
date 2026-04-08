/**
 * Confirm Dialog Component
 * 确认对话框组件
 */
import { useRef, useId } from "react";
import { AlertTriangle, X } from "lucide-react";
import { useI18n } from "../app/locale";
import { DialogShell } from "./DialogShell/DialogShell";
import "./ConfirmDialog.css";

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
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const messageId = useId();

  if (!isOpen) return null;

  return (
    <DialogShell
      isOpen={isOpen}
      onClose={onCancel}
      dialogRef={dialogRef}
      initialFocusRef={confirmButtonRef}
      className="confirm-dialog"
      overlayClassName="confirm-dialog-overlay"
      overlayAriaLabel="Dismiss confirm dialog backdrop"
      aria-labelledby={titleId}
      ariaDescribedBy={messageId}
    >
      <button
        type="button"
        className="confirm-dialog-close"
        onClick={onCancel}
        aria-label={t("common.close")}
      >
        <X size={18} />
      </button>

      <div className="confirm-dialog-content">
        <div className={`confirm-dialog-icon ${danger ? "danger" : ""}`}>
          <AlertTriangle size={32} />
        </div>

        <h3 id={titleId} className="confirm-dialog-title">
          {title}
        </h3>

        <p id={messageId} className="confirm-dialog-message">
          {message}
        </p>
      </div>

      <div className="confirm-dialog-actions">
        <button type="button" className="confirm-dialog-btn cancel" onClick={onCancel}>
          {cancelText ?? t("common.cancel")}
        </button>
        <button
          ref={confirmButtonRef}
          type="button"
          className={`confirm-dialog-btn confirm ${danger ? "danger" : ""}`}
          onClick={onConfirm}
        >
          {confirmText ?? t("common.confirm")}
        </button>
      </div>
    </DialogShell>
  );
}

export default ConfirmDialog;
