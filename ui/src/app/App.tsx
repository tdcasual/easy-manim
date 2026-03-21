import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { EvalsPage } from "./pages/EvalsPage";
import { MemoryPage } from "./pages/MemoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { TasksPage } from "./pages/TasksPage";
import { LoginPage } from "../features/auth/LoginPage";
import { useSession } from "../features/auth/useSession";
import { TaskDetailPage } from "../features/tasks/TaskDetailPage";

const NAV_ITEMS = [
  { to: "/tasks", label: "Tasks" },
  { to: "/memory", label: "Memory" },
  { to: "/profile", label: "Profile" },
  { to: "/evals", label: "Evals" }
] as const;

function RequireAuth() {
  const { isAuthenticated } = useSession();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function App() {
  return (
    <div className="appShell">
      <header className="topBar">
        <div className="topBarInner">
          <Link className="brand" to="/tasks" aria-label="easy-manim console home">
            <span className="brandMark" aria-hidden="true">
              em
            </span>
            <h1 className="brandTitle">easy-manim console</h1>
          </Link>
          <div className="topBarMeta">
            <span className="pill">Operator</span>
          </div>
        </div>
      </header>

      <div className="layout">
        <nav className="sideNav" aria-label="Primary">
          <div className="sideNavInner">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `navItem ${isActive ? "isActive" : ""}`}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <div className="sideNavFooter">
            <p className="muted small">Local-first. Agent-scoped.</p>
          </div>
        </nav>

        <main className="main" role="main">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth />}>
              <Route path="/" element={<TasksPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
              <Route path="/memory" element={<MemoryPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/evals" element={<EvalsPage />} />
            </Route>
          </Routes>
        </main>
      </div>
    </div>
  );
}
