import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { LoginPageV2 as LoginPage } from "../features/auth/LoginPageV2";
import { useSession } from "../features/auth/useSession";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { SkipLink } from "../components/SkipLink";
import { PageSkeleton } from "../components/Skeleton";
import { ToastProvider } from "../components/Toast";
import { useLocaleDocument } from "./locale";
import { Studio } from "../studio/Studio";

// Lazy-load legacy pages (kept as folded features)
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

// Auth guard
function RequireAuth() {
  const { isAuthenticated } = useSession();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

// Route loading state
function RouteLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <PageSkeleton />
    </div>
  );
}

// Main app component
export function App() {
  useLocaleDocument();

  return (
    <ToastProvider>
      <SkipLink />
      <ErrorBoundary>
        <div id="main-content" className="contents">
          <Suspense fallback={<RouteLoading />}>
            <Routes>
              {/* Login page */}
              <Route path="/login" element={<LoginPage />} />

              {/* Authenticated routes */}
              <Route element={<RequireAuth />}>
                {/* New Studio creative interface (default) */}
                <Route path="/" element={<Studio />} />
                <Route path="/studio" element={<Studio />} />

                {/* Legacy feature pages (folded, accessible via links) */}
                <Route path="/tasks" element={<TasksPageLazy />} />
                <Route path="/tasks/:taskId" element={<TaskDetailPageLazy />} />
                <Route path="/videos" element={<VideosPageLazy />} />
                <Route path="/threads/:threadId" element={<VideoThreadPageLazy />} />
                <Route path="/videos/:threadId" element={<VideoThreadPageLazy />} />
                <Route path="/memory" element={<MemoryPageLazy />} />
                <Route path="/profile" element={<ProfilePageLazy />} />
                <Route path="/evals" element={<EvalsPageLazy />} />
                <Route path="/evals/:runId" element={<EvalDetailPageLazy />} />
              </Route>
            </Routes>
          </Suspense>
        </div>
      </ErrorBoundary>
    </ToastProvider>
  );
}
