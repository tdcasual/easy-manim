/**
 * ARIA Live Region Component
 * 无障碍实时消息宣布组件
 */
import { useEffect, useRef } from "react";

interface ARIALiveRegionProps {
  message: string | null;
  level?: "polite" | "assertive";
  clearAfter?: number;
}

// 全局的 ARIA Live 区域，用于宣布状态变化
export function ARIALiveRegion({
  message,
  level = "polite",
  clearAfter = 3000,
}: ARIALiveRegionProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (message && ref.current) {
      // 清除消息以避免重复读取
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
