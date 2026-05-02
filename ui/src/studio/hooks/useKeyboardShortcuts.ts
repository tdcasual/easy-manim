/**
 * useKeyboardShortcuts - keyboard shortcuts hook.
 * Uses refs to store latest callbacks, avoiding frequent add/remove of listeners.
 */
import { useEffect, useRef } from "react";

interface UseKeyboardShortcutsOptions {
  isSettingsOpen: boolean;
  isHistoryOpen: boolean;
  isHelpOpen: boolean;
  onToggleSettings: () => void;
  onToggleHistory: () => void;
  onToggleHelp: () => void;
  onToggleTheme: () => void;
  onFocusInput: () => void;
}

export function useKeyboardShortcuts({
  isSettingsOpen,
  isHistoryOpen,
  isHelpOpen,
  onToggleSettings,
  onToggleHistory,
  onToggleHelp,
  onToggleTheme,
  onFocusInput,
}: UseKeyboardShortcutsOptions) {
  // Use refs to store latest state/callbacks to avoid frequent re-binding
  const stateRef = useRef({
    isSettingsOpen,
    isHistoryOpen,
    isHelpOpen,
    onToggleSettings,
    onToggleHistory,
    onToggleHelp,
    onToggleTheme,
    onFocusInput,
  });

  // Update ref
  useEffect(() => {
    stateRef.current = {
      isSettingsOpen,
      isHistoryOpen,
      isHelpOpen,
      onToggleSettings,
      onToggleHistory,
      onToggleHelp,
      onToggleTheme,
      onFocusInput,
    };
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const state = stateRef.current;

      // Ignore shortcuts inside inputs (except Escape)
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        if (e.key === "Escape") {
          (e.target as HTMLElement).blur();
        }
        return;
      }

      // ? - show/hide help (highest priority)
      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        state.onToggleHelp();
        return;
      }

      // Other shortcuts are disabled while help panel is open
      if (state.isHelpOpen) return;

      // / - focus input
      if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        state.onFocusInput();
        return;
      }

      // ESC - close panels
      if (e.key === "Escape") {
        if (state.isSettingsOpen) {
          state.onToggleSettings();
          return;
        }
        if (state.isHistoryOpen) {
          state.onToggleHistory();
          return;
        }
        return;
      }

      // H - open history
      if ((e.key === "h" || e.key === "H") && !state.isSettingsOpen) {
        state.onToggleHistory();
        return;
      }

      // S - open settings
      if ((e.key === "s" || e.key === "S") && !state.isHistoryOpen) {
        state.onToggleSettings();
        return;
      }

      // T - toggle theme
      if (e.key === "t" || e.key === "T") {
        state.onToggleTheme();
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []); // bind only once on mount
}
