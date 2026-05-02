/**
 * useTheme - theme management hook.
 * Manages day/night mode switching.
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

    // Detect system preference
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
    // Ignore storage errors
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(DEFAULT_THEME);
  const [isReady, setIsReady] = useState(false);

  // Read from storage on initialization
  useEffect(() => {
    const stored = getStoredTheme();
    setThemeState(stored);
    setIsReady(true);
  }, []);

  // Apply theme to document
  useEffect(() => {
    if (!isReady) return;

    document.documentElement.setAttribute("data-theme", theme);
    setStoredTheme(theme);
  }, [theme, isReady]);

  // Toggle theme
  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === "day" ? "night" : "day"));
  }, []);

  // Set specific theme
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
