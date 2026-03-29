import { useEffect, useRef, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

interface UseDialogA11yOptions<T extends HTMLElement> {
  isOpen: boolean;
  onClose: () => void;
  dialogRef: RefObject<T | null>;
  initialFocusRef?: RefObject<HTMLElement | null>;
  restoreFocusRef?: RefObject<HTMLElement | null>;
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (element) => !element.hasAttribute("disabled") && element.getAttribute("aria-hidden") !== "true"
  );
}

export function useDialogA11y<T extends HTMLElement>({
  isOpen,
  onClose,
  dialogRef,
  initialFocusRef,
  restoreFocusRef,
}: UseDialogA11yOptions<T>) {
  const previousFocusedRef = useRef<HTMLElement | null>(null);
  const previousOverflowRef = useRef("");

  useEffect(() => {
    if (!isOpen) return;

    previousFocusedRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    previousOverflowRef.current = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const dialog = dialogRef.current;
    if (!dialog) {
      return () => {
        document.body.style.overflow = previousOverflowRef.current;
      };
    }

    if (dialog.tabIndex < 0) {
      dialog.tabIndex = -1;
    }

    queueMicrotask(() => {
      const focusTarget = initialFocusRef?.current ?? getFocusableElements(dialog)[0] ?? dialog;
      focusTarget.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      const focusableElements = getFocusableElements(dialog);
      if (focusableElements.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey) {
        if (activeElement === firstElement || activeElement === dialog) {
          event.preventDefault();
          lastElement.focus();
        }
        return;
      }

      if (activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflowRef.current;

      const restoreTarget = restoreFocusRef?.current ?? previousFocusedRef.current;
      if (restoreTarget && restoreTarget.isConnected) {
        restoreTarget.focus();
        return;
      }

      if (restoreFocusRef) {
        queueMicrotask(() => {
          if (restoreFocusRef.current && restoreFocusRef.current.isConnected) {
            restoreFocusRef.current.focus();
          }
        });
      }
    };
  }, [dialogRef, initialFocusRef, isOpen, onClose, restoreFocusRef]);
}
