import { useState } from "react";
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { EvalsPage } from "./pages/EvalsPage";
import { MemoryPage } from "./pages/MemoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { TasksPage } from "./pages/TasksPage";
import { VideosPage } from "./pages/VideosPage";
import { LoginPage } from "../features/auth/LoginPage";
import { useSession } from "../features/auth/useSession";
import { TaskDetailPage } from "../features/tasks/TaskDetailPage";
import { EvalDetailPage } from "../features/evals/EvalDetailPage";
import { deleteCurrentSession } from "../lib/api";

const NAV_ITEMS = [
  { to: "/tasks", label: "任务", note: "创建任务、查看队列，并围绕结果快速迭代。", index: "01" },
  { to: "/videos", label: "视频", note: "回看最近可播放的结果，并快速继续修订。", index: "02" },
  { to: "/memory", label: "记忆", note: "把会话经验沉淀为可复用的长期上下文。", index: "03" },
  { to: "/profile", label: "画像", note: "管理智能体画像，并显式应用补丁。", index: "04" },
  { to: "/evals", label: "评测", note: "回看质量回归与评测运行结果。", index: "05" }
] as const;

function RequireAuth() {
  const { isAuthenticated } = useSession();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

function matchActiveItem(pathname: string) {
  return NAV_ITEMS.find((item) => pathname === item.to || pathname.startsWith(`${item.to}/`)) ?? NAV_ITEMS[0];
}

function AuthenticatedShell() {
  const location = useLocation();
  const { sessionToken, clearSessionToken } = useSession();
  const [logoutState, setLogoutState] = useState<"idle" | "loading">("idle");
  const activeItem = matchActiveItem(location.pathname);

  async function onSignOut() {
    if (!sessionToken || logoutState === "loading") {
      clearSessionToken();
      return;
    }

    setLogoutState("loading");
    try {
      await deleteCurrentSession(sessionToken);
    } catch {
      // We still clear local state so the operator can recover quickly.
    } finally {
      clearSessionToken();
      setLogoutState("idle");
    }
  }

  return (
    <div className="appShell">
      <header className="topBar">
        <div className="topBarInner">
          <Link className="brand" to="/tasks" aria-label="easy-manim console home">
            <span className="brandMark" aria-hidden="true">
              em
            </span>
            <div className="brandText">
              <h1 className="brandTitle">easy-manim console</h1>
              <p className="brandSubtitle">面向智能体工作流的视频生成控制台</p>
            </div>
          </Link>

          <div className="topBarMeta">
            <div className="contextBadge">
              <span className="contextLabel">当前焦点</span>
              <strong>{activeItem.label}</strong>
            </div>
            <span className="pill">会话已连接</span>
            <button className="button buttonQuiet" type="button" onClick={onSignOut}>
              {logoutState === "loading" ? "正在退出…" : "退出登录"}
            </button>
          </div>
        </div>
      </header>

      <div className="layout">
        <nav className="sideNav" aria-label="主导航">
          <div className="sideNavInner">
            <p className="sideNavEyebrow">工作流</p>
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `navItem ${isActive ? "isActive" : ""}`}
              >
                <span className="navItemIndex" aria-hidden="true">
                  {item.index}
                </span>
                <span className="navItemText">
                  <strong>{item.label}</strong>
                  <span>{item.note}</span>
                </span>
              </NavLink>
            ))}
          </div>
          <div className="sideNavFooter">
            <p className="muted small">先生成，再校验，再微调，把真正有效的经验沉淀下来。</p>
          </div>
        </nav>

        <main className="main" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AuthenticatedShell />}>
          <Route path="/" element={<TasksPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/videos" element={<VideosPage />} />
          <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/evals" element={<EvalsPage />} />
          <Route path="/evals/:runId" element={<EvalDetailPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
