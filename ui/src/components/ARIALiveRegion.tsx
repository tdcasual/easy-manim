/**
 * ARIA live region component
 * Accessibility live-message announcement component.
 */
import { useEffect, useRef } from "react";

interface ARIALiveRegionProps {
  message: string | null;
  level?: "polite" | "assertive";
  clearAfter?: number;
}

// Global ARIA live region for announcing state changes.
export function ARIALiveRegion({
  message,
  level = "polite",
  clearAfter = 3000,
}: ARIALiveRegionProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (message && ref.current) {
      // Clear message to avoid repeated reading
      const timer = setTimeout(() => {
        if (ref.current) {
          ref.current.textContent = "";
        }
      }, clearAfter);
      return () => clearTimeout(timer);
    }
  }, [message, clearAfter]);

  return (
    <div ref={ref} aria-live={level} aria-atomic="true" className="sr-only" role="status">
      {message}
    </div>
  );
}

export default ARIALiveRegion;
