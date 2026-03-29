/**
 * TasksPageV2 - Kawaii 二次元风格任务管理
 * 梦幻、柔和、可爱的设计风格
 */
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
import "./TasksPageV2.css";

// 🌸 Kawaii 状态指示器 - 带 emoji 和脉动动画
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
      icon={<span className="status-emoji">{s.icon}</span>}
      pulse={s.pulse}
    >
      {size === "md" && label}
    </KawaiiTag>
  );
}

// 🎬 Kawaii 视频卡片 - 带玻璃效果和圆角
function VideoThumb({ video }: { video: RecentVideoItem }) {
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const videoUrl = resolveApiUrl(video.latest_video_url);
  const displayTitle = video.display_title ?? video.task_id.slice(0, 8);

  return (
    <div className="video-thumb kawaii-card">
      <div className="thumb-preview">
        {previewUrl ? (
          <img src={previewUrl} alt={displayTitle} loading="lazy" />
        ) : (
          <div className="thumb-placeholder">
            <Play size={18} />
          </div>
        )}
        <div className="thumb-status">
          <StatusBadge status={video.status} size="sm" />
        </div>
        {videoUrl && (
          <a
            href={videoUrl}
            target="_blank"
            rel="noreferrer"
            className="thumb-play"
            onClick={(e) => e.stopPropagation()}
          >
            <Play size={14} fill="currentColor" />
          </a>
        )}
      </div>
      <p className="thumb-title">{displayTitle}</p>
    </div>
  );
}

// 📝 Kawaii 任务项 - 玻璃卡片效果
function TaskItem({ task, onCancel }: { task: TaskListItem; onCancel?: (id: string) => void }) {
  const { t } = useI18n();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const displayTitle = task.display_title ?? task.task_id.slice(0, 12);
  const canCancel = ["queued", "running"].includes(task.status.toLowerCase());

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="task-item kawaii-task-card">
      <Link to={`/tasks/${encodeURIComponent(task.task_id)}`} className="task-main">
        <StatusBadge status={task.status} />
        <div className="task-info">
          <p className="task-name">{displayTitle}</p>
          <p className="task-id">🆔 {task.task_id.slice(0, 8)}...</p>
        </div>
      </Link>

      <div className="task-actions" ref={menuRef}>
        <button
          className="action-btn kawaii-icon-btn"
          onClick={() => setShowMenu(!showMenu)}
          aria-label={t("tasks.moreActions")}
        >
          <MoreHorizontal size={18} />
        </button>

        {showMenu && (
          <div className="action-menu kawaii-menu">
            <Link
              to={`/tasks/${encodeURIComponent(task.task_id)}`}
              className="menu-item"
              onClick={() => setShowMenu(false)}
            >
              <Wand2 size={16} />
              <span>✨ {t("tasks.viewDetails")}</span>
            </Link>
            {canCancel && onCancel && (
              <button
                className="menu-item danger"
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

// 💬 Kawaii 快速输入区
interface QuickInputProps {
  onSubmit: (prompt: string) => void;
  creating?: boolean;
  requireAuth: () => boolean;
}

function QuickInput({ onSubmit, creating = false, requireAuth }: QuickInputProps) {
  const { list, t } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const quickPromptEmojis = ["🎨", "📊", "✨", "🌊"];
  const quickPrompts = list("tasks.quickPrompts").map((text, index) => ({
    emoji: quickPromptEmojis[index % quickPromptEmojis.length],
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

  return (
    <div className={`quick-input kawaii-input ${isFocused ? "focused" : ""}`}>
      <form onSubmit={handleSubmit}>
        <div className="input-bubble">
          <Sparkles size={18} className="input-icon sparkle-icon" />
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setTimeout(() => setIsFocused(false), 200)}
            placeholder={t("tasks.promptPlaceholder")}
            className="input-field"
          />
          <button
            type="submit"
            className={`send-btn kawaii-send ${creating ? "loading" : ""}`}
            disabled={!prompt.trim() || creating}
            aria-label={creating ? t("tasks.creating") : t("tasks.create")}
          >
            {creating ? <span className="spinner" aria-hidden="true" /> : <Plus size={18} />}
          </button>
        </div>

        {isFocused && (
          <div className="quick-chips">
            {quickPrompts.map((item) => (
              <button
                key={item.text}
                type="button"
                className="chip kawaii-chip"
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

// 🌸 统计卡片组件
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
  return (
    <div className={`stat-card stat-${color}`}>
      <div className="stat-icon-wrapper">{icon}</div>
      <div className="stat-content">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  );
}

export function TasksPageV2() {
  const { sessionToken } = useSession();
  const { t } = useI18n();
  const { ARIALiveRegion, announcePolite } = useARIAMessage();

  // 使用新的认证守卫
  const { showAuthModal, requireAuth, closeAuthModal } = useAuthGuard();

  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [videos, setVideos] = useState<RecentVideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "running" | "completed">("all");

  // 加载数据
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
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  const { success: toastSuccess, error: toastError } = useToast();

  // 创建任务
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

  // 取消任务
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

  // 过滤任务
  const filteredTasks = tasks
    .filter((t) => {
      if (activeTab === "running") return ["queued", "running"].includes(t.status.toLowerCase());
      if (activeTab === "completed") return t.status.toLowerCase() === "completed";
      return true;
    })
    .slice(0, 20);

  // 统计
  const stats = {
    total: tasks.length,
    running: tasks.filter((t) => ["queued", "running"].includes(t.status.toLowerCase())).length,
    completed: tasks.filter((t) => t.status.toLowerCase() === "completed").length,
  };

  return (
    <div className="tasks-page kawaii-page">
      {/* 🌈 梦幻渐变背景 */}
      <DreamyBackground />

      <ARIALiveRegion />

      {/* 页面标题 - 供测试使用 */}
      <h1 className="visually-hidden">{t("tasks.page.title")}</h1>

      {/* 🌸 头部统计 - Kawaii 卡片风格 */}
      <AnimatedContainer animation="slide-down" delay={0}>
        <div className="stats-bar kawaii-stats">
          <StatCard
            icon={<Clock size={18} className="stat-icon-inner running" />}
            value={stats.running}
            label={t("tasks.metric.active")}
            color="sky"
          />
          <StatCard
            icon={<CheckCircle2 size={18} className="stat-icon-inner completed" />}
            value={stats.completed}
            label={t("tasks.metric.completed")}
            color="mint"
          />
          <StatCard
            icon={<Film size={18} className="stat-icon-inner" />}
            value={stats.total}
            label={t("tasks.metric.total")}
            color="pink"
          />
          <button
            className="refresh-btn kawaii-refresh"
            onClick={loadData}
            disabled={loading}
            aria-label={t("tasks.refreshList")}
          >
            <RefreshCw size={18} className={loading ? "spin" : ""} />
          </button>
        </div>
      </AnimatedContainer>

      {/* 💬 快速输入 */}
      <AnimatedContainer animation="slide-up" delay={100}>
        <QuickInput onSubmit={handleCreate} creating={creating} requireAuth={requireAuth} />
      </AnimatedContainer>

      {/* 🏷️ 标签切换 - Kawaii 风格 */}
      <AnimatedContainer animation="slide-up" delay={150}>
        <div className="tabs kawaii-tabs">
          {[
            { key: "all" as const, label: t("tasks.tabs.all"), emoji: "🌸" },
            { key: "running" as const, label: t("tasks.tabs.running"), emoji: "🎬" },
            { key: "completed" as const, label: t("tasks.tabs.completed"), emoji: "✨" },
          ].map((tab, index) => (
            <button
              key={tab.key}
              className={`tab kawaii-tab ${activeTab === tab.key ? "active" : ""}`}
              onClick={() => setActiveTab(tab.key)}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <span className="tab-emoji">{tab.emoji}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </AnimatedContainer>

      {loadError && (
        <div className="task-load-error" role="alert">
          <AlertCircle size={18} />
          <div className="task-load-error-copy">
            <p>{loadError}</p>
            <span>{t("tasks.loadFailedHint")}</span>
          </div>
        </div>
      )}

      {/* 📝 任务列表 */}
      <div className="task-list kawaii-list">
        {loading && tasks.length === 0 ? (
          <div className="skeleton-list kawaii-skeleton">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="skeleton-item" style={{ animationDelay: `${i * 100}ms` }} />
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
              <HoverAnimation scale={1.01} lift={true}>
                <TaskItem task={task} onCancel={handleCancel} />
              </HoverAnimation>
            </AnimatedContainer>
          ))
        ) : loadError && tasks.length === 0 ? (
          <div className="task-load-fallback kawaii-empty" aria-hidden="true">
            <span className="empty-emoji">💔</span>
            <p>{loadError}</p>
            <span>{t("tasks.loadFailedHint")}</span>
          </div>
        ) : (
          <div className="empty-tip kawaii-empty">
            <span className="empty-emoji">🌸</span>
            <p>{t("tasks.noTasks")}</p>
            <span>{t("tasks.noTasksHint")}</span>
          </div>
        )}
      </div>

      {/* 🎬 最近视频 */}
      {videos.length > 0 && (
        <AnimatedContainer animation="fade" delay={200}>
          <div className="video-section kawaii-section">
            <h3 className="section-title kawaii-title">
              <span className="title-emoji">🎬</span>
              <span>{t("tasks.recentVideos")}</span>
              <Link to="/videos" className="view-all kawaii-link">
                {t("tasks.viewAll")} →
              </Link>
            </h3>
            <div className="video-grid">
              {videos.slice(0, 4).map((video, index) => (
                <AnimatedContainer
                  key={video.task_id}
                  animation="scale"
                  delay={index * 100}
                  trigger="in-view"
                >
                  <HoverAnimation scale={1.03} lift={true}>
                    <VideoThumb video={video} />
                  </HoverAnimation>
                </AnimatedContainer>
              ))}
            </div>
          </div>
        </AnimatedContainer>
      )}

      {/* 🔐 认证弹窗 - 默认折叠，需要时自动弹出 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
