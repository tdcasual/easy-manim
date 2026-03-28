/**
 * useKeyboardShortcuts - 键盘快捷键管理 Hook
 * 使用 ref 存储最新回调，避免频繁添加/移除事件监听器
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
  // 使用 ref 存储最新状态和回调，避免频繁重新绑定事件
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

  // 更新 ref
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

      // 忽略输入框内的快捷键（除了 Escape）
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        if (e.key === "Escape") {
          (e.target as HTMLElement).blur();
        }
        return;
      }

      // ? - 显示/隐藏帮助（优先级最高）
      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        state.onToggleHelp();
        return;
      }

      // 帮助面板打开时，其他快捷键不生效
      if (state.isHelpOpen) return;

      // / - 聚焦输入框
      if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        state.onFocusInput();
        return;
      }

      // ESC - 关闭面板
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

      // H - 打开历史
      if ((e.key === "h" || e.key === "H") && !state.isSettingsOpen) {
        state.onToggleHistory();
        return;
      }

      // S - 打开设置
      if ((e.key === "s" || e.key === "S") && !state.isHistoryOpen) {
        state.onToggleSettings();
        return;
      }

      // T - 切换主题
      if (e.key === "t" || e.key === "T") {
        state.onToggleTheme();
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []); // 只在组件挂载时绑定一次
}
