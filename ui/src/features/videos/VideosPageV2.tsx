import { useEffect, useState, useCallback, memo, useRef, useMemo } from "react";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import { Link } from "react-router-dom";
import {
  Play,
  Grid3X3,
  List,
  RefreshCw,
  Loader2,
  ArrowRight,
  AlertCircle,
  Search,
  Filter,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { useSession } from "../auth/useSession";
import { listRecentVideos, RecentVideoItem } from "../../lib/videosApi";
import { resolveApiUrl } from "../../lib/api";
import { useI18n } from "../../app/locale";
import { getStatusLabel } from "../../app/ui";
import { SkeletonCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/useARIAMessage";
import { useToast } from "../../components/useToast";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import "./VideosPageV2.css";

// 视频状态过滤器
type StatusFilter = "all" | "completed" | "running" | "queued" | "failed";

// 列表视图卡片
const VideoListItem = memo(function VideoListItem({ video }: { video: RecentVideoItem }) {
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const displayTitle = video.display_title ?? video.task_id;
  const { locale, t } = useI18n();

  const statusConfig: Record<
    string,
    { colorVar: string; icon: React.ReactNode; label: string; emoji: string }
  > = {
    completed: {
      colorVar: "var(--color-mint-500)",
      icon: <CheckCircle2 size={14} />,
      label: getStatusLabel("completed", locale),
      emoji: "✨",
    },
    rendering: {
      colorVar: "var(--color-sky-500)",
      icon: <Loader2 size={14} className="spin" />,
      label: getStatusLabel("rendering", locale),
      emoji: "🎨",
    },
    running: {
      colorVar: "var(--color-sky-500)",
      icon: <Loader2 size={14} className="spin" />,
      label: getStatusLabel("running", locale),
      emoji: "🎬",
    },
    queued: {
      colorVar: "var(--color-lemon-600)",
      icon: <Clock size={14} />,
      label: getStatusLabel("queued", locale),
      emoji: "⏳",
    },
    failed: {
      colorVar: "var(--color-pink-500)",
      icon: <XCircle size={14} />,
      label: getStatusLabel("failed", locale),
      emoji: "💦",
    },
  };

  const status = statusConfig[video.status.toLowerCase()] ?? {
    colorVar: "var(--color-cloud-600)",
    icon: null,
    label: video.status,
    emoji: "📹",
  };

  return (
    <div className="video-list-item-v2 hover-lift">
      <div className="video-list-thumb">
        {previewUrl ? (
          <img src={previewUrl} alt={displayTitle} loading="lazy" />
        ) : (
          <div className="video-list-placeholder">
            <Play size={24} />
          </div>
        )}
        <div
          className="video-list-status"
          style={{ background: `${status.colorVar}20`, color: status.colorVar }}
        >
          <span className="status-emoji">{status.emoji}</span>
          <span>{status.label}</span>
        </div>
      </div>

      <div className="video-list-content">
        <h4 className="video-list-title">{displayTitle}</h4>
        <div className="video-list-meta">
          <span className="video-list-id">{video.task_id}</span>
          <span className="video-list-date">
            {new Date(video.updated_at ?? Date.now()).toLocaleDateString()}
          </span>
        </div>
      </div>

      <div className="video-list-actions">
        <Link to={`/tasks/${encodeURIComponent(video.task_id)}`} className="video-list-link">
          <span>{t("videos.viewDetails")}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
});

// 网格视图卡片
const VideoGridCard = memo(function VideoGridCard({ video }: { video: RecentVideoItem }) {
  const videoUrl = resolveApiUrl(video.latest_video_url);
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const displayTitle = video.display_title ?? video.task_id;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const { locale, t } = useI18n();

  const statusConfig: Record<string, { colorVar: string; label: string; emoji: string }> = {
    completed: {
      colorVar: "var(--color-mint-500)",
      label: getStatusLabel("completed", locale),
      emoji: "✨",
    },
    rendering: {
      colorVar: "var(--color-sky-500)",
      label: getStatusLabel("rendering", locale),
      emoji: "🎨",
    },
    running: {
      colorVar: "var(--color-sky-500)",
      label: getStatusLabel("running", locale),
      emoji: "🎬",
    },
    queued: {
      colorVar: "var(--color-lemon-600)",
      label: getStatusLabel("queued", locale),
      emoji: "⏳",
    },
    failed: {
      colorVar: "var(--color-pink-500)",
      label: getStatusLabel("failed", locale),
      emoji: "💦",
    },
  };

  const status = statusConfig[video.status.toLowerCase()] ?? {
    colorVar: "var(--color-cloud-600)",
    label: video.status,
    emoji: "📹",
  };

  const togglePlay = useCallback(() => {
    const videoEl = videoRef.current;
    if (!videoEl) return;

    if (videoEl.paused) {
      videoEl
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => {});
    } else {
      videoEl.pause();
      setIsPlaying(false);
    }
  }, []);

  const handleVideoEnded = useCallback(() => {
    setIsPlaying(false);
  }, []);

  return (
    <div className="video-grid-card hover-lift">
      <div className="video-grid-preview">
        {videoUrl ? (
          <>
            <video
              ref={videoRef}
              poster={previewUrl ?? undefined}
              preload="metadata"
              muted
              loop
              aria-label={t("videos.videoLabel", { title: displayTitle })}
              onEnded={handleVideoEnded}
            >
              <source src={videoUrl} />
            </video>
            <button
              type="button"
              className={`video-play-control ${isPlaying ? "playing" : ""}`}
              onClick={togglePlay}
              aria-label={isPlaying ? t("videos.pauseVideo") : t("videos.playVideo")}
              aria-pressed={isPlaying}
            >
              {isPlaying ? (
                <span className="video-control-icon pause">
                  <span className="pause-bar" />
                  <span className="pause-bar" />
                </span>
              ) : (
                <Play size={20} fill="currentColor" />
              )}
            </button>
          </>
        ) : previewUrl ? (
          <img src={previewUrl} alt={displayTitle} loading="lazy" />
        ) : (
          <div className="video-grid-placeholder">
            <Play size={40} />
          </div>
        )}
        <div className="video-grid-overlay">
          <Link
            to={`/tasks/${encodeURIComponent(video.task_id)}`}
            className="video-grid-play"
            aria-label={t("videos.openDetails", { title: displayTitle })}
          >
            <Play size={24} fill="currentColor" />
          </Link>
        </div>
        <div
          className="video-grid-status"
          style={{ background: `${status.colorVar}20`, color: status.colorVar }}
        >
          <span className="status-emoji">{status.emoji}</span>
          <span>{status.label}</span>
        </div>
      </div>
      <div className="video-grid-info">
        <h4>{displayTitle}</h4>
        <p>{video.task_id}</p>
        <Link to={`/tasks/${encodeURIComponent(video.task_id)}`} className="video-grid-link">
          <span>{t("videos.viewDetails")}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
});

// 搜索筛选栏组件
function FilterBar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusChange,
  resultCount,
}: {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: StatusFilter;
  onStatusChange: (status: StatusFilter) => void;
  resultCount: number;
}) {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);

  const statusOptions: { value: StatusFilter; label: string; color: string; emoji: string }[] = [
    {
      value: "all",
      label: t("videos.filterStatus.all"),
      color: "var(--color-cloud-600)",
      emoji: "🌈",
    },
    {
      value: "completed",
      label: t("videos.filterStatus.completed"),
      color: "var(--color-mint-500)",
      emoji: "✨",
    },
    {
      value: "running",
      label: t("videos.filterStatus.running"),
      color: "var(--color-sky-500)",
      emoji: "🎬",
    },
    {
      value: "queued",
      label: t("videos.filterStatus.queued"),
      color: "var(--color-lemon-600)",
      emoji: "⏳",
    },
    {
      value: "failed",
      label: t("videos.filterStatus.failed"),
      color: "var(--color-pink-500)",
      emoji: "💦",
    },
  ];

  return (
    <div className="video-filter-bar glass">
      <div className="filter-search">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          placeholder={t("videos.searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="search-input"
        />
        {searchQuery && (
          <button
            type="button"
            className="search-clear"
            onClick={() => onSearchChange("")}
            aria-label={t("videos.clearSearch")}
          >
            <span>×</span>
          </button>
        )}
      </div>

      <button
        type="button"
        className={`filter-toggle ${isExpanded ? "active" : ""}`}
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-label={t("videos.filter")}
      >
        <Filter size={16} />
        <span>{t("videos.filter")}</span>
      </button>

      <div className="filter-result-count">
        <span className="result-emoji">📹</span>
        <span>{t("videos.resultCount", { count: resultCount })}</span>
      </div>

      {isExpanded && (
        <div className="filter-options">
          {statusOptions.map((option) => (
            <button
              type="button"
              key={option.value}
              className={`filter-chip ${statusFilter === option.value ? "active" : ""}`}
              onClick={() => onStatusChange(option.value)}
              style={
                statusFilter === option.value
                  ? {
                      background: `${option.color}20`,
                      color: option.color,
                      borderColor: option.color,
                    }
                  : undefined
              }
            >
              <span className="chip-emoji">{option.emoji}</span>
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// 装饰云朵组件
function CloudDecoration() {
  return (
    <>
      <div className="cloud cloud-1">☁️</div>
      <div className="cloud cloud-2">☁️</div>
      <div className="cloud cloud-3">☁️</div>
      <div className="sparkle sparkle-1">✨</div>
      <div className="sparkle sparkle-2">✨</div>
      <div className="sparkle sparkle-3">🌸</div>
    </>
  );
}

// 主组件
export function VideosPageV2() {
  const { sessionToken } = useSession();
  const { t } = useI18n();
  const { error: showError } = useToast();
  const [items, setItems] = useState<RecentVideoItem[]>([]);
  const { status, error, startLoading, setErrorState, succeed } = useAsyncStatus();
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  const { showAuthModal, closeAuthModal } = useAuthGuard();

  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    startLoading();
    try {
      const response = await listRecentVideos(sessionToken, 50);
      setItems(Array.isArray(response.items) ? response.items : []);
      succeed();
      announcePolite(t("videos.loaded", { count: response.items?.length ?? 0 }));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("common.loadingFailed");
      setErrorState(errorMsg);
      showError(errorMsg);
      announcePolite(t("videos.loadFailed", { error: errorMsg }));
    }
  }, [sessionToken, announcePolite, t, showError, startLoading, succeed, setErrorState]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // 筛选逻辑
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // 状态筛选
      if (statusFilter !== "all") {
        const itemStatus = item.status.toLowerCase();
        if (statusFilter === "running" && !["running", "rendering"].includes(itemStatus)) {
          return false;
        }
        if (statusFilter !== "running" && itemStatus !== statusFilter) {
          return false;
        }
      }

      // 搜索筛选
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const title = (item.display_title ?? "").toLowerCase();
        const taskId = item.task_id.toLowerCase();
        return title.includes(query) || taskId.includes(query);
      }

      return true;
    });
  }, [items, statusFilter, searchQuery]);

  return (
    <div className="page-v2 kawaii-page">
      <CloudDecoration />
      <ARIALiveRegion />

      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">
            <span className="eyebrow-emoji">🎬</span>
            <span>{t("videos.page.eyebrow")}</span>
          </div>
          <h1 className="page-title-v2">
            {t("videos.page.title")}
            <span className="title-emoji">✨</span>
          </h1>
          <p className="page-description-v2">{t("videos.page.description")}</p>
        </div>
        <div className="page-header-actions">
          <div className="view-toggle glass" role="group" aria-label={t("videos.viewToggle")}>
            <button
              type="button"
              className={viewMode === "grid" ? "active" : ""}
              onClick={() => setViewMode("grid")}
              aria-label={t("videos.gridView")}
              aria-pressed={viewMode === "grid"}
            >
              <Grid3X3 size={18} />
            </button>
            <button
              type="button"
              className={viewMode === "list" ? "active" : ""}
              onClick={() => setViewMode("list")}
              aria-label={t("videos.listView")}
              aria-pressed={viewMode === "list"}
            >
              <List size={18} />
            </button>
          </div>
          <button
            type="button"
            className="refresh-btn"
            onClick={refresh}
            disabled={status === "loading"}
            aria-busy={status === "loading"}
          >
            {status === "loading" ? (
              <Loader2 size={18} className="spin" />
            ) : (
              <RefreshCw size={18} />
            )}
            <span>{t("videos.refresh")}</span>
          </button>
        </div>
      </div>

      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        resultCount={filteredItems.length}
      />

      {error && (
        <div className="form-error-v2" role="alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {status === "loading" && items.length === 0 ? (
        <div className="videos-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : filteredItems.length > 0 ? (
        <div className={`videos-${viewMode}`}>
          {viewMode === "grid"
            ? filteredItems.map((video) => <VideoGridCard key={video.task_id} video={video} />)
            : filteredItems.map((video) => <VideoListItem key={video.task_id} video={video} />)}
        </div>
      ) : (
        <div className="empty-state-v2 glass">
          <div className="empty-emoji">🎭</div>
          <p>
            {searchQuery || statusFilter !== "all" ? t("videos.noResults") : t("videos.noPlayable")}
          </p>
          <span>
            {searchQuery || statusFilter !== "all"
              ? t("videos.tryAdjustFilter")
              : t("videos.noPlayableHint")}
          </span>
        </div>
      )}

      {/* 🔐 认证弹窗 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
