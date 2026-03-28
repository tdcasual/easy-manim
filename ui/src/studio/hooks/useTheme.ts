/**
 * useTheme - 主题管理 Hook
 * 管理白天/夜间模式切换
 */
import { useEffect, useState, useCallback } from "react";

type Theme = "day" | "night";

const THEME_KEY = "easy_manim_theme";
const DEFAULT_THEME: Theme = "day";

function getStoredTheme(): Theme {
  if (typeof window === "undefined") return DEFAULT_THEME;

  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "day" || stored === "night") {
      return stored;
    }

    // 检测系统偏好
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "night" : "day";
  } catch {
    return DEFAULT_THEME;
  }
}

function setStoredTheme(theme: Theme): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // 忽略存储错误
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(DEFAULT_THEME);
  const [isReady, setIsReady] = useState(false);

  // 初始化时从存储读取
  useEffect(() => {
    const stored = getStoredTheme();
    setThemeState(stored);
    setIsReady(true);
  }, []);

  // 应用主题到 document
  useEffect(() => {
    if (!isReady) return;

    document.documentElement.setAttribute("data-theme", theme);
    setStoredTheme(theme);
  }, [theme, isReady]);

  // 切换主题
  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === "day" ? "night" : "day"));
  }, []);

  // 设置指定主题
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
  }, []);

  return {
    theme,
    isNight: theme === "night",
    isDay: theme === "day",
    toggleTheme,
    setTheme,
    isReady,
  };
}
