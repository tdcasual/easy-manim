import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  RefreshCw,
  Play,
  Clock,
  CheckCircle2,
  MoreHorizontal,
  Trash2,
  Wand2,
  Sparkles,
  Film,
  AlertCircle,
} from "lucide-react";
import { useSession } from "../auth/useSession";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import { createTask, listTasks, TaskListItem, cancelTask } from "../../lib/tasksApi";
import { listRecentVideos, RecentVideoItem } from "../../lib/videosApi";
import { resolveApiUrl } from "../../lib/api";
import { useI18n } from "../../app/locale";
import { getStatusLabel } from "../../app/ui";
import { useARIAMessage } from "../../components/useARIAMessage";
import { useToast } from "../../components/useToast";
import { DreamyBackground } from "../../components/GradientBackground";
import { KawaiiTag } from "../../components/KawaiiTag";
import { AnimatedContainer, HoverAnimation } from "../../components/AnimatedContainer";
import { cn } from "../../lib/utils";

const TASK_AUTO_REFRESH_INTERVAL_MS = 5000;
const ACTIVE_TASK_STATUSES = new Set(["queued", "running"]);
const QUICK_PROMPT_EMOJIS = ["🎨", "📊", "✨", "🌊"];

function normalizeTaskStatus(status: string) {
  return status.toLowerCase();
}

function isActiveTaskStatus(status: string) {
  return ACTIVE_TASK_STATUSES.has(normalizeTaskStatus(status));
}

function canAutoRefreshTasks(tasks: TaskListItem[]) {
  if (typeof document === "undefined") {
    return tasks.some((task) => isActiveTaskStatus(task.status));
  }

  return (
    document.visibilityState === "visible" && tasks.some((task) => isActiveTaskStatus(task.status))
  );
}

function StatusBadge({ status, size = "md" }: { status: string; size?: "sm" | "md" }) {
  const { locale } = useI18n();

  const variantMap: Record<
    string,
    {
      variant: "pink" | "mint" | "sky" | "lavender" | "peach" | "default";
      icon: string;
      pulse: boolean;
    }
  > = {
    completed: { variant: "mint", icon: "✨", pulse: false },
    running: { variant: "sky", icon: "🎬", pulse: true },
    queued: { variant: "lavender", icon: "⏳", pulse: true },
    failed: { variant: "peach", icon: "💔", pulse: false },
    cancelled: { variant: "default", icon: "🚫", pulse: false },
  };

  const s = variantMap[status.toLowerCase()] ?? variantMap.queued;
  const label = getStatusLabel(status.toLowerCase(), locale);
  const tagSize = size === "sm" ? "sm" : "md";

  return (
    <KawaiiTag
      variant={s.variant}
      size={tagSize}
      icon={<span className="text-xs">{s.icon}</span>}
      pulse={s.pulse}
    >
      {size === "md" && label}
    </KawaiiTag>
  );
}

function VideoThumb({ video }: { video: RecentVideoItem }) {
  const { t } = useI18n();
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const videoUrl = resolveApiUrl(video.latest_video_url);
  const displayTitle = video.display_title ?? video.task_id?.slice(0, 8) ?? "";

  return (
    <div className="group overflow-hidden rounded-2xl border border-cloud-200 bg-white shadow-sm transition-colors transition-transform transition-shadow hover:-translate-y-1 hover:shadow-lg dark:border-cloud-800 dark:bg-cloud-900">
      <div className="relative aspect-[16/10] overflow-hidden bg-gradient-to-br from-pink-50 to-mint-50 dark:from-cloud-800 dark:to-cloud-800">
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={displayTitle}
            loading="lazy"
            decoding="async"
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-pink-400">
            <Play size={18} />
          </div>
        )}
        <div className="absolute right-2 top-2">
          <StatusBadge status={video.status} size="sm" />
        </div>
        {videoUrl && (
          <a
            href={videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t("tasks.playVideo", { title: displayTitle })}
            className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            onClick={(e) => e.stopPropagation()}
          >
            <Play size={14} fill="currentColor" className="text-white drop-shadow-md" />
          </a>
        )}
      </div>
      <p className="truncate px-3 py-2 text-sm font-medium text-cloud-700 dark:text-cloud-200">
        {displayTitle}
      </p>
    </div>
  );
}

function TaskItem({ task, onCancel }: { task: TaskListItem; onCancel?: (id: string) => void }) {
  const { t } = useI18n();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const displayTitle = task.display_title ?? task.task_id?.slice(0, 12) ?? "";
  const canCancel = ["queued", "running"].includes(task.status.toLowerCase());

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowMenu(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, []);

  return (
    <div className="group flex items-center gap-3 rounded-2xl border border-cloud-200 bg-white px-4 py-3 shadow-sm transition-colors transition-transform transition-shadow hover:-translate-y-0.5 hover:bg-cloud-50 hover:shadow-md dark:border-cloud-800 dark:bg-cloud-900 dark:hover:bg-cloud-800 sm:gap-4 sm:px-5 sm:py-4">
      <Link
        to={`/tasks/${encodeURIComponent(task.task_id)}`}
        className="flex min-w-0 flex-1 items-center gap-3 text-inherit no-underline sm:gap-4"
      >
        <StatusBadge status={task.status} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-cloud-800 dark:text-cloud-100 sm:text-base">
            {displayTitle}
          </p>
          <p className="truncate text-xs text-cloud-500 dark:text-cloud-400">
            🆔 {task.task_id?.slice(0, 8) ?? ""}...
          </p>
        </div>
      </Link>

      <div className="relative" ref={menuRef}>
        <button
          type="button"
          ref={triggerRef}
          className="flex h-11 w-11 items-center justify-center rounded-xl bg-cloud-100 text-cloud-600 transition-colors transition-transform hover:scale-110 hover:rotate-12 hover:bg-pink-100 hover:text-pink-500 dark:bg-cloud-800 dark:text-cloud-400 dark:hover:bg-pink-900/30"
          onClick={() => setShowMenu(!showMenu)}
          aria-label={t("tasks.moreActions")}
          aria-expanded={showMenu}
        >
          <MoreHorizontal size={18} />
        </button>

        {showMenu && (
          <div className="absolute right-0 top-full z-40 mt-2 min-w-[10rem] rounded-xl border border-cloud-200 bg-white p-1.5 shadow-lg dark:border-cloud-800 dark:bg-cloud-900">
            <Link
              to={`/tasks/${encodeURIComponent(task.task_id)}`}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-cloud-700 transition-colors hover:bg-pink-50 hover:text-pink-600 dark:text-cloud-200 dark:hover:bg-pink-900/20"
              onClick={() => setShowMenu(false)}
            >
              <Wand2 size={16} />
              <span>✨ {t("tasks.viewDetails")}</span>
            </Link>
            {canCancel && onCancel && (
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-peach-600 transition-colors hover:bg-peach-50 dark:text-peach-400 dark:hover:bg-peach-900/20"
                onClick={() => {
                  onCancel(task.task_id);
                  setShowMenu(false);
                }}
              >
                <Trash2 size={16} />
                <span>🗑️ {t("taskDetail.cancelTask")}</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface QuickInputProps {
  onSubmit: (prompt: string) => void;
  creating?: boolean;
  requireAuth: () => boolean;
}

function QuickInput({ onSubmit, creating = false, requireAuth }: QuickInputProps) {
  const { list, t } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const blurTimeoutRef = useRef<number | null>(null);

  const quickPrompts = list("tasks.quickPrompts").map((text, index) => ({
    emoji: QUICK_PROMPT_EMOJIS[index % QUICK_PROMPT_EMOJIS.length],
    text,
  }));

  const submitPrompt = (nextPrompt: string) => {
    const trimmedPrompt = nextPrompt.trim();
    if (!trimmedPrompt) return;
    if (!requireAuth()) return;
    onSubmit(trimmedPrompt);
    setPrompt("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitPrompt(prompt);
  };

  useEffect(() => {
    return () => {
      if (blurTimeoutRef.current !== null) {
        window.clearTimeout(blurTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      className={cn(
        "rounded-full border border-cloud-200 bg-white p-1.5 shadow-md transition-colors transition-shadow dark:border-cloud-800 dark:bg-cloud-900",
        isFocused && "border-pink-200 shadow-lg shadow-pink-100/30"
      )}
    >
      <form onSubmit={handleSubmit}>
        <div className="flex items-center gap-3 px-3 py-2">
          <Sparkles size={18} className="shrink-0 text-pink-400" />
          <input
            type="text"
            aria-label={t("tasks.promptLabel")}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onFocus={() => {
              if (blurTimeoutRef.current !== null) {
                window.clearTimeout(blurTimeoutRef.current);
                blurTimeoutRef.current = null;
              }
              setIsFocused(true);
            }}
            onBlur={() => {
              if (blurTimeoutRef.current !== null) {
                window.clearTimeout(blurTimeoutRef.current);
              }
              blurTimeoutRef.current = window.setTimeout(() => {
                setIsFocused(false);
                blurTimeoutRef.current = null;
              }, 200);
            }}
            placeholder={t("tasks.promptPlaceholder")}
            className="min-w-0 flex-1 bg-transparent text-sm text-cloud-800 outline-none placeholder:text-cloud-500 dark:text-cloud-100"
          />
          <button
            type="submit"
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white shadow-md transition-colors",
              "bg-gradient-to-br from-pink-400 to-pink-500 shadow-pink-200/40",
              "hover:scale-110 hover:rotate-90 hover:shadow-lg",
              "disabled:cursor-not-allowed disabled:opacity-60 disabled:scale-100 disabled:rotate-0"
            )}
            disabled={!prompt.trim() || creating}
            aria-label={creating ? t("tasks.creating") : t("tasks.create")}
          >
            {creating ? (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              <Plus size={18} />
            )}
          </button>
        </div>

        {isFocused && (
          <div className="flex flex-wrap gap-2 px-3 pb-3 pt-2">
            {quickPrompts.map((item) => (
              <button
                key={item.text}
                type="button"
                className="flex items-center gap-1.5 rounded-full border border-pink-200 bg-pink-50 px-3 py-1.5 text-xs font-medium text-pink-600 transition-colors transition-transform transition-shadow hover:-translate-y-0.5 hover:bg-pink-100 hover:shadow-sm dark:border-pink-900/30 dark:bg-pink-900/20 dark:text-pink-300"
                onClick={() => submitPrompt(item.text)}
              >
                <span>{item.emoji}</span>
                <span>{item.text}</span>
              </button>
            ))}
          </div>
        )}
      </form>
    </div>
  );
}

function StatCard({
  icon,
  value,
  label,
  color,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
  color: "pink" | "mint" | "sky" | "lavender";
}) {
  const colorClass = {
    pink: "bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-300",
    mint: "bg-mint-100 text-mint-600 dark:bg-mint-900/30 dark:text-mint-300",
    sky: "bg-sky-100 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300",
    lavender: "bg-lavender-100 text-lavender-600 dark:bg-lavender-900/30 dark:text-lavender-300",
  }[color];

  return (
    <div className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl border border-cloud-200 bg-white px-4 py-3 shadow-sm transition-colors transition-transform transition-shadow hover:-translate-y-1 hover:shadow-md dark:border-cloud-800 dark:bg-cloud-900 sm:gap-4 sm:px-5 sm:py-4">
      <div
        className={cn(
          "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl sm:h-12 sm:w-12",
          colorClass
        )}
      >
        {icon}
      </div>
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-xl font-bold leading-none text-cloud-800 dark:text-cloud-100 sm:text-2xl">
          {value}
        </span>
        <span className="truncate text-xs font-medium text-cloud-500 dark:text-cloud-400">
          {label}
        </span>
      </div>
    </div>
  );
}

export function TasksPageV2() {
  const { sessionToken } = useSession();
  const { t } = useI18n();
  const { ARIALiveRegion, announcePolite } = useARIAMessage();

  const { showAuthModal, requireAuth, closeAuthModal } = useAuthGuard();

  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [videos, setVideos] = useState<RecentVideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "running" | "completed">("all");

  const loadData = useCallback(async () => {
    if (!sessionToken) {
      setTasks([]);
      setVideos([]);
      setLoadError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const [tasksRes, videosRes] = await Promise.all([
        listTasks(sessionToken),
        listRecentVideos(sessionToken, 8),
      ]);
      setTasks(tasksRes.items ?? []);
      setVideos(videosRes.items ?? []);
    } catch {
      setLoadError(t("tasks.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [sessionToken, t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;
  const loadDataRef = useRef(loadData);
  loadDataRef.current = loadData;

  useEffect(() => {
    if (!sessionToken) {
      return;
    }

    const interval = window.setInterval(() => {
      if (canAutoRefreshTasks(tasksRef.current)) {
        void loadDataRef.current();
      }
    }, TASK_AUTO_REFRESH_INTERVAL_MS);

    return () => window.clearInterval(interval);
  }, [sessionToken]);

  useEffect(() => {
    if (!sessionToken || typeof document === "undefined") {
      return;
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void loadDataRef.current();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [sessionToken]);

  const { success: toastSuccess, error: toastError } = useToast();

  const handleCreate = async (prompt: string) => {
    if (!sessionToken || creating) return;
    setCreating(true);
    try {
      const res = await createTask(prompt, sessionToken);
      if (res?.task_id) {
        const title = res.display_title ?? prompt.slice(0, 20);
        setTasks((prev) => [
          {
            task_id: res.task_id,
            status: "queued",
            display_title: title,
          },
          ...prev,
        ]);
        toastSuccess(t("tasks.taskCreated", { title }));
        announcePolite(t("tasks.taskCreated", { title }));
        loadData();
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error && error.message ? error.message : t("common.loadingFailed");
      const failureMessage = t("tasks.createFailed", { error: errorMessage });
      toastError(failureMessage);
      announcePolite(failureMessage);
    } finally {
      setCreating(false);
    }
  };

  const handleCancel = async (taskId: string) => {
    if (!sessionToken) return;
    try {
      await cancelTask(taskId, sessionToken);
      setTasks((prev) =>
        prev.map((t) => (t.task_id === taskId ? { ...t, status: "cancelled" } : t))
      );
      announcePolite(t("tasks.cancelled"));
    } catch {
      announcePolite(t("tasks.cancelFailed"));
    }
  };

  const filteredTasks = tasks
    .filter((t) => {
      const status = normalizeTaskStatus(t.status);
      if (activeTab === "running") return isActiveTaskStatus(status);
      if (activeTab === "completed") return status === "completed";
      return true;
    })
    .slice(0, 20);

  const stats = {
    total: tasks.length,
    running: tasks.filter((t) => isActiveTaskStatus(t.status)).length,
    completed: tasks.filter((t) => normalizeTaskStatus(t.status) === "completed").length,
  };

  return (
    <div className="relative mx-auto min-h-screen max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <DreamyBackground />

      <ARIALiveRegion />

      <h1 className="sr-only">{t("tasks.page.title")}</h1>

      <AnimatedContainer animation="slide-down" delay={0}>
        <div className="mb-5 flex flex-wrap items-stretch gap-3 sm:mb-6 sm:gap-4">
          <StatCard
            icon={<Clock size={18} />}
            value={stats.running}
            label={t("tasks.metric.active")}
            color="sky"
          />
          <StatCard
            icon={<CheckCircle2 size={18} />}
            value={stats.completed}
            label={t("tasks.metric.completed")}
            color="mint"
          />
          <StatCard
            icon={<Film size={18} />}
            value={stats.total}
            label={t("tasks.metric.total")}
            color="pink"
          />
          <button
            type="button"
            className="flex h-auto w-12 shrink-0 items-center justify-center rounded-2xl border border-cloud-200 bg-white text-cloud-500 shadow-sm transition-colors transition-transform transition-shadow hover:rotate-180 hover:scale-110 hover:bg-pink-100 hover:text-pink-500 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:rotate-0 disabled:hover:scale-100 dark:border-cloud-800 dark:bg-cloud-900 dark:text-cloud-400 sm:w-14"
            onClick={loadData}
            disabled={loading}
            aria-label={t("tasks.refreshList")}
          >
            <RefreshCw size={18} className={cn(loading && "animate-spin")} />
          </button>
        </div>
      </AnimatedContainer>

      <AnimatedContainer animation="slide-up" delay={100}>
        <QuickInput onSubmit={handleCreate} creating={creating} requireAuth={requireAuth} />
      </AnimatedContainer>

      <AnimatedContainer animation="slide-up" delay={150}>
        <div className="mb-5 flex gap-2 overflow-x-auto pb-1 sm:mb-6 sm:gap-3" role="tablist">
          {[
            { key: "all" as const, label: t("tasks.tabs.all"), emoji: "🌸" },
            { key: "running" as const, label: t("tasks.tabs.running"), emoji: "🎬" },
            { key: "completed" as const, label: t("tasks.tabs.completed"), emoji: "✨" },
          ].map((tab) => (
            <button
              type="button"
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              aria-controls="tasks-tabpanel"
              className={cn(
                "flex shrink-0 items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-medium transition-colors sm:px-5 sm:py-2.5",
                activeTab === tab.key
                  ? "border-transparent bg-gradient-to-r from-pink-400 to-peach-400 text-white shadow-md shadow-pink-200/40"
                  : "border-cloud-200 bg-white text-cloud-600 hover:-translate-y-0.5 hover:border-pink-200 hover:bg-pink-50 hover:text-pink-500 hover:shadow-sm dark:border-cloud-800 dark:bg-cloud-900 dark:text-cloud-400 dark:hover:bg-pink-900/20"
              )}
              onClick={() => setActiveTab(tab.key)}
            >
              <span>{tab.emoji}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </AnimatedContainer>

      {loadError && (
        <div
          className="mb-5 flex items-start gap-3 rounded-2xl border border-pink-200 bg-white px-4 py-3 text-sm text-pink-700 shadow-sm dark:border-pink-900/30 dark:bg-cloud-900 dark:text-pink-300"
          role="alert"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <div className="flex flex-col gap-1">
            <p>{loadError}</p>
            <span className="text-xs text-cloud-500 dark:text-cloud-400">
              {t("tasks.loadFailedHint")}
            </span>
          </div>
        </div>
      )}

      <div id="tasks-tabpanel" role="tabpanel" className="flex flex-col gap-3">
        {loading && tasks.length === 0 ? (
          <div className="flex flex-col gap-3">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-[72px] animate-shimmer rounded-2xl bg-gradient-to-r from-cloud-100 via-cloud-200 to-cloud-100"
                style={{ backgroundSize: "200% 100%", animationDelay: `${i * 100}ms` }}
              />
            ))}
          </div>
        ) : filteredTasks.length > 0 ? (
          filteredTasks.map((task, index) => (
            <AnimatedContainer
              key={task.task_id}
              animation="slide-up"
              delay={index * 50}
              trigger="in-view"
            >
              <HoverAnimation scale={1.01} lift>
                <TaskItem task={task} onCancel={handleCancel} />
              </HoverAnimation>
            </AnimatedContainer>
          ))
        ) : loadError && tasks.length === 0 ? (
          <div
            className="flex flex-col items-center rounded-2xl border border-cloud-200 bg-white px-6 py-12 text-center text-cloud-500 shadow-sm dark:border-cloud-800 dark:bg-cloud-900"
            role="alert"
          >
            <span className="mb-4 text-6xl">💔</span>
            <p className="text-lg font-semibold text-cloud-700 dark:text-cloud-200">{loadError}</p>
            <span className="text-sm text-cloud-500 dark:text-cloud-400">
              {t("tasks.loadFailedHint")}
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center rounded-2xl border border-cloud-200 bg-white px-6 py-12 text-center text-cloud-500 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
            <span className="mb-4 text-6xl">🌸</span>
            <p className="text-lg font-semibold text-cloud-700 dark:text-cloud-200">
              {t("tasks.noTasks")}
            </p>
            <span className="text-sm text-cloud-500 dark:text-cloud-400">
              {t("tasks.noTasksHint")}
            </span>
          </div>
        )}
      </div>

      {videos.length > 0 && (
        <AnimatedContainer animation="fade" delay={200}>
          <div className="mt-8">
            <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-cloud-700 dark:text-cloud-200">
              <span className="text-xl">🎬</span>
              <span>{t("tasks.recentVideos")}</span>
              <Link
                to="/videos"
                className="ml-auto rounded-full bg-pink-50 px-3 py-1 text-xs font-medium text-pink-500 transition-colors transition-transform hover:translate-x-1 hover:bg-pink-100 dark:bg-pink-900/20 dark:hover:bg-pink-900/30"
              >
                {t("tasks.viewAll")} →
              </Link>
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {videos.slice(0, 4).map((video, index) => (
                <AnimatedContainer
                  key={video.task_id}
                  animation="fade"
                  delay={index * 100}
                  trigger="in-view"
                >
                  <HoverAnimation scale={1.03} lift>
                    <VideoThumb video={video} />
                  </HoverAnimation>
                </AnimatedContainer>
              ))}
            </div>
          </div>
        </AnimatedContainer>
      )}

      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
