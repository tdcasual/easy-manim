import { type ReactNode, type RefObject } from "react";
import { Dialog, DialogContent } from "../ui/dialog";

export interface DialogShellProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  role?: "dialog" | "alertdialog";
  ariaLabel?: string;
  ariaLabelledBy?: string;
  ariaDescribedBy?: string;
  // Compatibility props (no longer used but kept to avoid breaking callers)
  dialogRef?: RefObject<HTMLDivElement | null>;
  initialFocusRef?: RefObject<HTMLElement | null>;
  restoreFocusRef?: RefObject<HTMLElement | null>;
  overlayClassName?: string;
  overlayAriaLabel?: string;
}

export function DialogShell({
  isOpen,
  onClose,
  children,
  className,
  ariaLabel,
  ariaLabelledBy,
  ariaDescribedBy,
}: DialogShellProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className={className}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        aria-describedby={ariaDescribedBy}
        onInteractOutside={onClose}
        onEscapeKeyDown={onClose}
      >
        {children}
      </DialogContent>
    </Dialog>
  );
}
