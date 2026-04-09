import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppRouter } from "./app/router";
import { readLocale, syncDocumentLocale } from "./app/locale";

// 导入运行时设计系统样式（顺序很重要）。
// `theme-v2.css` 保留为遗留参考样式，当前运行时不直接挂载它。
import "./styles/tailwind.css";
import "./styles/kawaii-theme.css";
import "./styles/animations.css";
// Legacy theme compatibility for pages not yet migrated to Tailwind
import "./styles/tokens.css";
import "./styles/ghibli-theme.css";
import "./styles/page-shell-v2.css";
import "./styles/reset.css";

// 同步语言和主题
syncDocumentLocale(readLocale());

// 初始化主题
try {
  const theme = localStorage.getItem("easy_manim_theme") ?? "day";
  document.documentElement.setAttribute("data-theme", theme);
} catch {
  document.documentElement.setAttribute("data-theme", "day");
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>
);
