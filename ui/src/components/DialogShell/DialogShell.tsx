import { type ReactNode, type RefObject } from "react";
import { useDialogA11y } from "../useDialogA11y";
import styles from "./DialogShell.module.css";

export interface DialogShellProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  dialogRef: RefObject<HTMLDivElement>;
  initialFocusRef?: RefObject<HTMLElement>;
  restoreFocusRef?: RefObject<HTMLElement>;
  className?: string;
  overlayClassName?: string;
  role?: "dialog" | "alertdialog";
  ariaLabel?: string;
  ariaLabelledBy?: string;
  ariaDescribedBy?: string;
  overlayAriaLabel?: string;
}

export function DialogShell({
  isOpen,
  onClose,
  children,
  dialogRef,
  initialFocusRef,
  restoreFocusRef,
  className,
  overlayClassName,
  role = "dialog",
  ariaLabel,
  ariaLabelledBy,
  ariaDescribedBy,
  overlayAriaLabel = "Dismiss dialog backdrop",
}: DialogShellProps) {
  useDialogA11y({
    isOpen,
    onClose,
    dialogRef,
    initialFocusRef,
    restoreFocusRef,
  });

  if (!isOpen) return null;

  return (
    <>
      <button
        type="button"
        className={`${styles.overlay} ${overlayClassName ?? ""}`.trim()}
        onClick={onClose}
        aria-label={overlayAriaLabel}
        tabIndex={-1}
      />
      <div
        ref={dialogRef as RefObject<HTMLDivElement>}
        className={className}
        role={role}
        aria-modal="true"
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        aria-describedby={ariaDescribedBy}
      >
        {children}
      </div>
    </>
  );
}
