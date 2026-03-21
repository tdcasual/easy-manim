import { Link, NavLink, Route, Routes } from "react-router-dom";

import { EvalsPage } from "./pages/EvalsPage";
import { MemoryPage } from "./pages/MemoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { TasksPage } from "./pages/TasksPage";

const NAV_ITEMS = [
  { to: "/tasks", label: "Tasks" },
  { to: "/memory", label: "Memory" },
  { to: "/profile", label: "Profile" },
  { to: "/evals", label: "Evals" }
] as const;

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
            <Route path="/" element={<TasksPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/evals" element={<EvalsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

