import { useEffect, useCallback, useRef, useId, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
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
  confirmText = "确认",
  cancelText = "取消",
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const messageId = useId();

  const getFocusableElements = useCallback(() => {
    if (!dialogRef.current) return [] as HTMLElement[];

    return Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
  }, []);

  // ESC 键关闭
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") {
      onCancel();
      return;
    }

    if (e.key !== "Tab") {
      return;
    }

    const focusableElements = getFocusableElements();
    if (!focusableElements.length) {
      e.preventDefault();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    const activeElement = document.activeElement as HTMLElement | null;

    if (!activeElement || !dialogRef.current?.contains(activeElement)) {
      e.preventDefault();
      (e.shiftKey ? lastElement : firstElement).focus();
      return;
    }

    if (e.shiftKey && activeElement === firstElement) {
      e.preventDefault();
      lastElement.focus();
      return;
    }

    if (!e.shiftKey && activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
    }
  }, [getFocusableElements, onCancel]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }

    const frame = window.requestAnimationFrame(() => {
      confirmButtonRef.current?.focus();
    });

    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      if (previousFocusRef.current?.isConnected) {
        previousFocusRef.current.focus();
      }
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div 
      className="confirm-dialog-overlay" 
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={messageId}
    >
      <div 
        ref={dialogRef}
        className="confirm-dialog"
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
      >
        <button 
          className="confirm-dialog-close"
          onClick={onCancel}
          aria-label="关闭"
        >
          <X size={18} />
        </button>

        <div className="confirm-dialog-content">
          <div className={`confirm-dialog-icon ${danger ? 'danger' : ''}`}>
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
          <button
            type="button"
            className="confirm-dialog-btn cancel"
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            className={`confirm-dialog-btn confirm ${danger ? 'danger' : ''}`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export function useConfirm() {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions>({
    title: "",
    message: "",
  });
  const [resolveRef, setResolveRef] = useState<((value: boolean) => void) | null>(null);

  const confirm = useCallback((newOptions: ConfirmOptions): Promise<boolean> => {
    setOptions(newOptions);
    setIsOpen(true);
    
    return new Promise((resolve) => {
      setResolveRef(() => resolve);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    setIsOpen(false);
    resolveRef?.(true);
    setResolveRef(null);
  }, [resolveRef]);

  const handleCancel = useCallback(() => {
    setIsOpen(false);
    resolveRef?.(false);
    setResolveRef(null);
  }, [resolveRef]);

  const ConfirmDialogComponent = useCallback(() => (
    <ConfirmDialog
      isOpen={isOpen}
      {...options}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  ), [isOpen, options, handleConfirm, handleCancel]);

  return {
    confirm,
    ConfirmDialog: ConfirmDialogComponent,
  };
}
