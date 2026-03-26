import { useEffect, useCallback } from "react";
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
  // ESC 键关闭
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") {
      onCancel();
    }
  }, [onCancel]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div 
      className="confirm-dialog-overlay" 
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
    >
      <div 
        className="confirm-dialog"
        onClick={(e) => e.stopPropagation()}
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
          
          <h3 id="confirm-title" className="confirm-dialog-title">
            {title}
          </h3>
          
          <p id="confirm-message" className="confirm-dialog-message">
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
            type="button"
            className={`confirm-dialog-btn confirm ${danger ? 'danger' : ''}`}
            onClick={onConfirm}
            autoFocus
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

// Hook for using confirm dialog
import { useState } from "react";

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
