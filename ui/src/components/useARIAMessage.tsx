/**
 * ARIA Message Hook
 * 管理 ARIA 实时区域消息宣布
 */
import React, { useState, useCallback } from "react";
import { ARIALiveRegion } from "./ARIALiveRegion";

export function useARIAMessage() {
  const [message, setMessage] = useState<string | null>(null);
  const [level, setLevel] = useState<"polite" | "assertive">("polite");

  const announce = useCallback(
    (msg: string, options?: { level?: "polite" | "assertive"; duration?: number }) => {
      setLevel(options?.level ?? "polite");
      setMessage(msg);

      // 自动清除
      setTimeout(() => {
        setMessage(null);
      }, options?.duration ?? 3000);
    },
    []
  );

  const announcePolite = useCallback(
    (msg: string, duration?: number) => {
      announce(msg, { level: "polite", duration });
    },
    [announce]
  );

  const announceAssertive = useCallback(
    (msg: string, duration?: number) => {
      announce(msg, { level: "assertive", duration });
    },
    [announce]
  );

  return {
    message,
    level,
    announce,
    announcePolite,
    announceAssertive,
    ARIALiveRegion: () => <ARIALiveRegion message={message} level={level} />,
  };
}

export default useARIAMessage;
