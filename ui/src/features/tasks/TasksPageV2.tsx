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
          aria-label="更多操作"
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
              <span>✨ 详情</span>
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
                <span>🗑️ 取消</span>
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
  const { t } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const quickPrompts = [
    { emoji: "🎨", text: "制作LOGO动画" },
    { emoji: "📊", text: "数据可视化" },
    { emoji: "✨", text: "文字特效" },
    { emoji: "🌊", text: "粒子效果" },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    // 检查认证，未认证时自动弹窗
    if (!requireAuth()) return;
    onSubmit(prompt.trim());
    setPrompt("");
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
            placeholder={t("tasks.quickPlaceholder") ?? "✨ 想创作什么动画呢？"}
            className="input-field"
          />
          <button
            type="submit"
            className={`send-btn kawaii-send ${creating ? "loading" : ""}`}
            disabled={!prompt.trim() || creating}
            aria-label={creating ? "创建中..." : "创建任务"}
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
                onClick={() => onSubmit(item.text)}
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
  const [creating, setCreating] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "running" | "completed">("all");

  // 加载数据
  const loadData = useCallback(async () => {
    if (!sessionToken) return;
    setLoading(true);
    try {
      const [tasksRes, videosRes] = await Promise.all([
        listTasks(sessionToken),
        listRecentVideos(sessionToken, 8),
      ]);
      setTasks(tasksRes.items ?? []);
      setVideos(videosRes.items ?? []);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

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
        setTasks((prev) => [
          {
            task_id: res.task_id,
            status: "queued",
            display_title: res.display_title ?? prompt.slice(0, 20),
          },
          ...prev,
        ]);
        toastSuccess(t("tasks.created") ?? "✨ 任务创建成功！");
        announcePolite(t("tasks.created") || "任务创建成功");
        loadData();
      }
    } catch {
      toastError(t("tasks.createFailed") || "💔 创建失败，请重试");
      announcePolite(t("tasks.createFailed") || "创建失败");
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
      announcePolite(t("tasks.cancelled") || "任务已取消");
    } catch {
      announcePolite(t("tasks.cancelFailed") || "取消失败");
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
      <h1 className="visually-hidden">任务管理</h1>

      {/* 🌸 头部统计 - Kawaii 卡片风格 */}
      <AnimatedContainer animation="slide-down" delay={0}>
        <div className="stats-bar kawaii-stats">
          <StatCard
            icon={<Clock size={18} className="stat-icon-inner running" />}
            value={stats.running}
            label="进行中"
            color="sky"
          />
          <StatCard
            icon={<CheckCircle2 size={18} className="stat-icon-inner completed" />}
            value={stats.completed}
            label="已完成"
            color="mint"
          />
          <StatCard
            icon={<Film size={18} className="stat-icon-inner" />}
            value={stats.total}
            label="总计"
            color="pink"
          />
          <button
            className="refresh-btn kawaii-refresh"
            onClick={loadData}
            disabled={loading}
            aria-label="刷新"
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
            { key: "all" as const, label: "🌸 全部", emoji: "🌸" },
            { key: "running" as const, label: "🎬 进行中", emoji: "🎬" },
            { key: "completed" as const, label: "✨ 已完成", emoji: "✨" },
          ].map((tab, index) => (
            <button
              key={tab.key}
              className={`tab kawaii-tab ${activeTab === tab.key ? "active" : ""}`}
              onClick={() => setActiveTab(tab.key)}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <span className="tab-emoji">{tab.emoji}</span>
              <span className="tab-label">{tab.label.replace(/^./, "").trim()}</span>
            </button>
          ))}
        </div>
      </AnimatedContainer>

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
        ) : (
          <div className="empty-tip kawaii-empty">
            <span className="empty-emoji">🌸</span>
            <p>还没有任务呢</p>
            <span>创建一个新任务开始创作之旅吧 ✨</span>
          </div>
        )}
      </div>

      {/* 🎬 最近视频 */}
      {videos.length > 0 && (
        <AnimatedContainer animation="fade" delay={200}>
          <div className="video-section kawaii-section">
            <h3 className="section-title kawaii-title">
              <span className="title-emoji">🎬</span>
              <span>最近生成</span>
              <Link to="/videos" className="view-all kawaii-link">
                查看全部 →
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
