import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppRouter } from "./app/router";
import { readLocale, syncDocumentLocale } from "./app/locale";

// 导入设计系统样式（顺序很重要）
import "./styles/tokens.css";
import "./styles/ghibli-theme.css";

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
