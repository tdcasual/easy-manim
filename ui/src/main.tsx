import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppRouter } from "./app/router";
import { readLocale, syncDocumentLocale } from "./app/locale";

// 导入运行时设计系统样式（顺序很重要）。
// `theme-v2.css` 保留为遗留参考样式，当前运行时不直接挂载它。
import "./styles/runtime.css";

// 同步语言和主题
syncDocumentLocale(readLocale());

// 初始化主题
try {
  const theme = localStorage.getItem("easy_manim_theme") ?? "day";
  document.documentElement.setAttribute("data-theme", theme);
} catch {
  document.documentElement.setAttribute("data-theme", "day");
}

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("Missing root element");
}
createRoot(rootEl).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>
);
