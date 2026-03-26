import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppRouter } from "./app/router";

// 新主题 (V2)
import "./styles/theme-v2.css";

// Lucide icons (需要安装)
// npm install lucide-react

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>
);
