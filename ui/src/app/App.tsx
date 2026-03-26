import { useState, useEffect, useRef, lazy, Suspense } from "react";
import { 
  Link, 
  NavLink, 
  Navigate, 
  Outlet, 
  Route, 
  Routes, 
  useLocation,
  useNavigate 
} from "react-router-dom";
import { 
  Layers, 
  Play, 
  Brain, 
  UserCircle, 
  BarChart3, 
  LogOut, 
  Command,
  Sparkles,
  Menu,
  X,
  ChevronRight,
  Monitor
} from "lucide-react";

import { LoginPage } from "../features/auth/LoginPage";
import { useSession } from "../features/auth/useSession";
import { deleteCurrentSession } from "../lib/api";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { PageSkeleton } from "../components/Skeleton";
import "./App.css";

// 导航项配置
const NAV_ITEMS = [
  { 
    to: "/tasks", 
    icon: Layers, 
    label: "任务", 
    description: "创建与管理",
    color: "#00d4ff"
  },
  { 
    to: "/videos", 
    icon: Play, 
    label: "视频", 
    description: "回看与修订",
    color: "#8b5cf6"
  },
  { 
    to: "/memory", 
    icon: Brain, 
    label: "记忆", 
    description: "经验沉淀",
    color: "#ec4899"
  },
  { 
    to: "/profile", 
    icon: UserCircle, 
    label: "画像", 
    description: "智能体配置",
    color: "#10b981"
  },
  { 
    to: "/evals", 
    icon: BarChart3, 
    label: "评测", 
    description: "质量验证",
    color: "#f59e0b"
  }
] as const;

// 认证守卫
function RequireAuth() {
  const { isAuthenticated } = useSession();
  const location = useLocation();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

// Logo 组件
function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <Link to="/tasks" className="logo">
      <div className="logo-icon">
        <Sparkles size={24} />
      </div>
      {!collapsed && (
        <div className="logo-text">
          <span className="logo-title">easy-manim</span>
          <span className="logo-subtitle">AI Video Studio</span>
        </div>
      )}
    </Link>
  );
}

// 导航项组件
function NavItem({ 
  item, 
  collapsed 
}: { 
  item: typeof NAV_ITEMS[number]; 
  collapsed: boolean;
}) {
  const Icon = item.icon;
  
  return (
    <NavLink 
      to={item.to} 
      className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
      style={{ '--accent-color': item.color } as React.CSSProperties}
    >
      <div className="nav-icon">
        <Icon size={20} />
      </div>
      {!collapsed && (
        <div className="nav-content">
          <span className="nav-label">{item.label}</span>
          <span className="nav-description">{item.description}</span>
        </div>
      )}
      {!collapsed && <ChevronRight size={14} className="nav-arrow" />}
    </NavLink>
  );
}

// 侧边栏组件
function Sidebar({ 
  collapsed, 
  onToggle,
  mobileOpen,
  onMobileClose
}: { 
  collapsed: boolean; 
  onToggle: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}) {
  const { sessionToken, clearSessionToken } = useSession();
  const [logoutLoading, setLogoutLoading] = useState(false);
  const navigate = useNavigate();
  
  async function handleLogout() {
    if (!sessionToken) {
      clearSessionToken();
      return;
    }
    
    setLogoutLoading(true);
    try {
      await deleteCurrentSession(sessionToken);
    } finally {
      clearSessionToken();
      setLogoutLoading(false);
      navigate("/login");
    }
  }
  
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-header">
        <Logo collapsed={collapsed} />
        <button 
          className="sidebar-toggle"
          onClick={onToggle}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
      </div>
      
      <nav className="sidebar-nav">
        <div className="nav-section">
          {!collapsed && <span className="nav-section-title">工作流</span>}
          <div className="nav-items">
            {NAV_ITEMS.map(item => (
              <NavItem key={item.to} item={item} collapsed={collapsed} />
            ))}
          </div>
        </div>
      </nav>
      
      <div className="sidebar-footer">
        <button 
          className="logout-btn"
          onClick={handleLogout}
          disabled={logoutLoading}
        >
          <LogOut size={18} />
          {!collapsed && (
            <span>{logoutLoading ? "退出中..." : "退出登录"}</span>
          )}
        </button>
      </div>
    </aside>
  );
}

// 用户菜单组件
function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const { sessionToken, clearSessionToken } = useSession();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);
  
  // 点击外部关闭菜单
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);
  
  async function handleLogout() {
    if (sessionToken) {
      await deleteCurrentSession(sessionToken);
    }
    clearSessionToken();
    navigate("/login");
  }
  
  return (
    <div className="user-menu" ref={menuRef}>
      <button 
        className="user-avatar"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="用户菜单"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Command size={18} />
      </button>
      
      {isOpen && (
        <div className="user-menu-dropdown" role="menu">
          <div className="user-menu-header">
            <span className="user-menu-title">当前会话</span>
          </div>
          <button 
            className="user-menu-item"
            onClick={handleLogout}
            role="menuitem"
          >
            <LogOut size={16} />
            <span>退出登录</span>
          </button>
        </div>
      )}
    </div>
  );
}

// 顶部栏组件
function Topbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const location = useLocation();
  const currentPage = NAV_ITEMS.find(item => 
    location.pathname.startsWith(item.to)
  );
  
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button 
          className="mobile-menu-btn"
          onClick={onMenuClick}
          aria-label="打开菜单"
        >
          <Menu size={20} />
        </button>
        <div className="page-info">
          <div className="page-title" role="heading" aria-level={1}>
            {currentPage?.label || "控制台"}
          </div>
          <span className="page-breadcrumb">
            easy-manim / {currentPage?.label || "首页"}
          </span>
        </div>
      </div>
      
      <div className="topbar-right">
        <div className="status-indicator">
          <Monitor size={14} />
          <span className="status-dot online"></span>
          <span className="status-text">系统就绪</span>
        </div>
        <UserMenu />
      </div>
    </header>
  );
}

// 认证后外壳
function AuthenticatedShell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  
  // 页面切换时滚动到顶部
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [location.pathname]);
  
  // 路由变化时关闭移动端菜单
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);
  
  return (
    <div className="app-shell">
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />
      
      {/* 移动端菜单遮罩 */}
      {mobileMenuOpen && (
        <div 
          className="mobile-overlay"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      
      <div className={`main-area ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Topbar onMenuClick={() => setMobileMenuOpen(true)} />
        
        <main className="main-content">
          <div className="content-wrapper animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

// 路由加载状态
function RouteLoading() {
  return (
    <div className="route-loading">
      <PageSkeleton />
    </div>
  );
}

// 主应用组件
export function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<RouteLoading />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AuthenticatedShell />}>
              <Route path="/" element={<Navigate to="/tasks" replace />} />
              <Route path="/tasks" element={<TasksPageLazy />} />
              <Route path="/tasks/:taskId" element={<TaskDetailPageLazy />} />
              <Route path="/videos" element={<VideosPageLazy />} />
              <Route path="/memory" element={<MemoryPageLazy />} />
              <Route path="/profile" element={<ProfilePageLazy />} />
              <Route path="/evals" element={<EvalsPageLazy />} />
              <Route path="/evals/:runId" element={<EvalDetailPageLazy />} />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

// 懒加载页面组件

const TasksPageLazy = lazy(() => import("../features/tasks/TasksPageV2").then(m => ({ default: m.TasksPageV2 })));
const TaskDetailPageLazy = lazy(() => import("../features/tasks/TaskDetailPageV2").then(m => ({ default: m.TaskDetailPageV2 })));
const VideosPageLazy = lazy(() => import("../features/videos/VideosPageV2").then(m => ({ default: m.VideosPageV2 })));
const MemoryPageLazy = lazy(() => import("../features/memory/MemoryPageV2").then(m => ({ default: m.MemoryPageV2 })));
const ProfilePageLazy = lazy(() => import("../features/profile/ProfilePageV2").then(m => ({ default: m.ProfilePageV2 })));
const EvalsPageLazy = lazy(() => import("../features/evals/EvalsPageV2").then(m => ({ default: m.EvalsPageV2 })));
const EvalDetailPageLazy = lazy(() => import("../features/evals/EvalDetailPageV2").then(m => ({ default: m.EvalDetailPageV2 })));
