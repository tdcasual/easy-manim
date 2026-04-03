import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { LoginPageV2 as LoginPage } from "../features/auth/LoginPageV2";
import { useSession } from "../features/auth/useSession";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { PageSkeleton } from "../components/Skeleton";
import { ToastProvider } from "../components/Toast";
import { useLocaleDocument } from "./locale";
import { Studio } from "../studio/Studio";
import "./App.css";

// 懒加载原有页面（作为折叠功能保留）
const TasksPageLazy = lazy(() =>
  import("../features/tasks/TasksPageV2").then((m) => ({ default: m.TasksPageV2 }))
);
const TaskDetailPageLazy = lazy(() =>
  import("../features/tasks/TaskDetailPageV2").then((m) => ({ default: m.TaskDetailPageV2 }))
);
const VideosPageLazy = lazy(() =>
  import("../features/videos/VideosPageV2").then((m) => ({ default: m.VideosPageV2 }))
);
const VideoThreadPageLazy = lazy(() =>
  import("../features/videoThreads/VideoThreadPage").then((m) => ({ default: m.VideoThreadPage }))
);
const MemoryPageLazy = lazy(() =>
  import("../features/memory/MemoryPageV2").then((m) => ({ default: m.MemoryPageV2 }))
);
const ProfilePageLazy = lazy(() =>
  import("../features/profile/ProfilePageV2").then((m) => ({ default: m.ProfilePageV2 }))
);
const EvalsPageLazy = lazy(() =>
  import("../features/evals/EvalsPageV2").then((m) => ({ default: m.EvalsPageV2 }))
);
const EvalDetailPageLazy = lazy(() =>
  import("../features/evals/EvalDetailPageV2").then((m) => ({ default: m.EvalDetailPageV2 }))
);

// 认证守卫
function RequireAuth() {
  const { isAuthenticated } = useSession();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

// 路由加载状态
function RouteLoading() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <PageSkeleton />
    </div>
  );
}

// 主应用组件
export function App() {
  useLocaleDocument();

  return (
    <ToastProvider>
      <ErrorBoundary>
        <Suspense fallback={<RouteLoading />}>
          <Routes>
            {/* 登录页 */}
            <Route path="/login" element={<LoginPage />} />

            {/* 认证后路由 */}
            <Route element={<RequireAuth />}>
              {/* 新的 Studio 创作界面（默认） */}
              <Route path="/" element={<Studio />} />
              <Route path="/studio" element={<Studio />} />

              {/* 原有功能页面（折叠，通过链接访问） */}
              <Route path="/tasks" element={<TasksPageLazy />} />
              <Route path="/tasks/:taskId" element={<TaskDetailPageLazy />} />
              <Route path="/videos" element={<VideosPageLazy />} />
              <Route path="/videos/:threadId" element={<VideoThreadPageLazy />} />
              <Route path="/memory" element={<MemoryPageLazy />} />
              <Route path="/profile" element={<ProfilePageLazy />} />
              <Route path="/evals" element={<EvalsPageLazy />} />
              <Route path="/evals/:runId" element={<EvalDetailPageLazy />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </ToastProvider>
  );
}
