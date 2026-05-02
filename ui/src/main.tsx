import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppRouter } from "./app/router";
import { readLocale, syncDocumentLocale } from "./app/locale";

// Import runtime design-system styles (order matters).
// `theme-v2.css` is kept as a legacy reference and is not mounted at runtime.
import "./styles/runtime.css";

// Sync locale and theme
syncDocumentLocale(readLocale());

// Initialize theme
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
