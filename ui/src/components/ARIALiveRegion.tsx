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
    <div
      ref={ref}
      aria-live={level}
      aria-atomic="true"
      className="sr-only"
      role="status"
    >
      {message}
    </div>
  );
}

// 使用自定义 hook 管理 ARIA 消息
import { useState, useCallback } from "react";

export function useARIAMessage() {
  const [message, setMessage] = useState<string | null>(null);
  const [level, setLevel] = useState<"polite" | "assertive">("polite");

  const announce = useCallback((
    msg: string,
    options?: { level?: "polite" | "assertive"; duration?: number }
  ) => {
    setLevel(options?.level || "polite");
    setMessage(msg);
    
    // 自动清除
    setTimeout(() => {
      setMessage(null);
    }, options?.duration || 3000);
  }, []);

  const announcePolite = useCallback((msg: string, duration?: number) => {
    announce(msg, { level: "polite", duration });
  }, [announce]);

  const announceAssertive = useCallback((msg: string, duration?: number) => {
    announce(msg, { level: "assertive", duration });
  }, [announce]);

  return {
    message,
    level,
    announce,
    announcePolite,
    announceAssertive,
    ARIALiveRegion: () => (
      <ARIALiveRegion message={message} level={level} />
    ),
  };
}
