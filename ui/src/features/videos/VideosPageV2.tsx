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
import { cn } from "../../lib/utils";

type StatusFilter = "all" | "completed" | "running" | "queued" | "failed";

const VideoListItem = memo(function VideoListItem({ video }: { video: RecentVideoItem }) {
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const displayTitle = video.display_title ?? video.task_id;
  const detailHref = video.thread_id
    ? `/threads/${encodeURIComponent(video.thread_id)}`
    : `/tasks/${encodeURIComponent(video.task_id)}`;
  const { locale, t } = useI18n();

  const statusConfig: Record<
    string,
    { className: string; icon: React.ReactNode; label: string; emoji: string }
  > = {
    completed: {
      className: "bg-mint-100 text-mint-700 dark:bg-mint-900/30 dark:text-mint-300",
      icon: <CheckCircle2 size={14} />,
      label: getStatusLabel("completed", locale),
      emoji: "✨",
    },
    rendering: {
      className: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
      icon: <Loader2 size={14} className="animate-spin" />,
      label: getStatusLabel("rendering", locale),
      emoji: "🎨",
    },
    running: {
      className: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
      icon: <Loader2 size={14} className="animate-spin" />,
      label: getStatusLabel("running", locale),
      emoji: "🎬",
    },
    queued: {
      className: "bg-lemon-100 text-lemon-700 dark:bg-amber-900/30 dark:text-amber-300",
      icon: <Clock size={14} />,
      label: getStatusLabel("queued", locale),
      emoji: "⏳",
    },
    failed: {
      className: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300",
      icon: <XCircle size={14} />,
      label: getStatusLabel("failed", locale),
      emoji: "💦",
    },
  };

  const status = statusConfig[video.status.toLowerCase()] ?? {
    className: "bg-cloud-100 text-cloud-700 dark:bg-slate-800 dark:text-cloud-300",
    icon: null,
    label: video.status,
    emoji: "📹",
  };

  return (
    <div className="group flex flex-wrap items-center gap-4 rounded-2xl border border-white/60 bg-white/60 p-3 shadow-sm backdrop-blur-sm transition-all hover:translate-x-2 hover:border-pink-200 hover:bg-white/80 hover:shadow-md dark:border-white/10 dark:bg-slate-900/60 dark:hover:bg-slate-900/80 sm:flex-nowrap sm:p-4">
      <div className="relative h-auto w-full shrink-0 overflow-hidden rounded-xl bg-gradient-to-br from-pink-100 to-mint-100 aspect-video sm:w-32">
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={displayTitle}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-pink-400">
            <Play size={24} />
          </div>
        )}
        <div
          className={cn(
            "absolute bottom-1 left-1 flex items-center gap-1 rounded-full border border-white/70 px-2 py-0.5 text-[11px] font-semibold backdrop-blur-sm",
            status.className
          )}
        >
          <span>{status.emoji}</span>
          <span>{status.label}</span>
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <h4 className="truncate text-sm font-semibold text-cloud-800 dark:text-cloud-100">
          {displayTitle}
        </h4>
        <div className="flex gap-3 text-xs text-cloud-500 dark:text-cloud-400">
          <span className="font-mono">{video.task_id}</span>
          <span>{new Date(video.updated_at ?? Date.now()).toLocaleDateString()}</span>
        </div>
      </div>

      <div className="w-full shrink-0 sm:w-auto">
        <Link
          to={detailHref}
          className="flex w-full items-center justify-center gap-1 rounded-full bg-gradient-to-r from-mint-400 to-sky-400 px-3 py-2 text-xs font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md hover:gap-2 sm:w-auto"
        >
          <span>{t("videos.viewDetails")}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
});

const VideoGridCard = memo(function VideoGridCard({ video }: { video: RecentVideoItem }) {
  const videoUrl = resolveApiUrl(video.latest_video_url);
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const displayTitle = video.display_title ?? video.task_id;
  const detailHref = video.thread_id
    ? `/threads/${encodeURIComponent(video.thread_id)}`
    : `/tasks/${encodeURIComponent(video.task_id)}`;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const { locale, t } = useI18n();

  const statusConfig: Record<string, { className: string; label: string; emoji: string }> = {
    completed: {
      className: "bg-mint-100 text-mint-700 dark:bg-mint-900/30 dark:text-mint-300",
      label: getStatusLabel("completed", locale),
      emoji: "✨",
    },
    rendering: {
      className: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
      label: getStatusLabel("rendering", locale),
      emoji: "🎨",
    },
    running: {
      className: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
      label: getStatusLabel("running", locale),
      emoji: "🎬",
    },
    queued: {
      className: "bg-lemon-100 text-lemon-700 dark:bg-amber-900/30 dark:text-amber-300",
      label: getStatusLabel("queued", locale),
      emoji: "⏳",
    },
    failed: {
      className: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300",
      label: getStatusLabel("failed", locale),
      emoji: "💦",
    },
  };

  const status = statusConfig[video.status.toLowerCase()] ?? {
    className: "bg-cloud-100 text-cloud-700 dark:bg-slate-800 dark:text-cloud-300",
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
    <div className="group overflow-hidden rounded-2xl border border-white/60 bg-white/60 shadow-md backdrop-blur-sm transition-all hover:-translate-y-1 hover:border-pink-200 hover:shadow-lg dark:border-white/10 dark:bg-slate-900/60">
      <div className="relative aspect-video overflow-hidden rounded-t-2xl bg-gradient-to-br from-pink-100 to-mint-100 dark:from-slate-800 dark:to-slate-800">
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
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            >
              <source src={videoUrl} />
            </video>
            <button
              type="button"
              className={cn(
                "absolute bottom-3 left-3 z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 border-white shadow-md transition-all hover:scale-110",
                isPlaying
                  ? "bg-gradient-to-br from-pink-400 to-pink-500 text-white"
                  : "bg-white/80 text-pink-500 hover:bg-white"
              )}
              onClick={togglePlay}
              aria-label={isPlaying ? t("videos.pauseVideo") : t("videos.playVideo")}
              aria-pressed={isPlaying}
            >
              {isPlaying ? (
                <span className="flex gap-[3px]">
                  <span className="h-3 w-1 rounded-sm bg-current" />
                  <span className="h-3 w-1 rounded-sm bg-current" />
                </span>
              ) : (
                <Play size={20} fill="currentColor" />
              )}
            </button>
          </>
        ) : previewUrl ? (
          <img
            src={previewUrl}
            alt={displayTitle}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-pink-400">
            <Play size={40} />
          </div>
        )}
        <div className="absolute inset-0 flex items-center justify-center bg-pink-200/30 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
          <Link
            to={detailHref}
            className="flex h-16 w-16 scale-80 items-center justify-center rounded-full border-[3px] border-white bg-gradient-to-br from-pink-400 to-peach-400 text-white shadow-lg transition-transform duration-300 group-hover:scale-100"
            aria-label={t("videos.openDetails", { title: displayTitle })}
          >
            <Play size={24} fill="currentColor" />
          </Link>
        </div>
        <div
          className={cn(
            "absolute right-3 top-3 flex items-center gap-1 rounded-full border border-white/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide backdrop-blur-sm shadow-sm",
            status.className
          )}
        >
          <span className="text-sm">{status.emoji}</span>
          <span>{status.label}</span>
        </div>
      </div>
      <div className="flex flex-col gap-1 p-4">
        <h4 className="truncate text-base font-semibold text-cloud-800 dark:text-cloud-100">
          {displayTitle}
        </h4>
        <p className="truncate text-xs font-mono text-cloud-500 dark:text-cloud-400">
          {video.task_id}
        </p>
        <Link
          to={detailHref}
          className="mt-1 flex items-center gap-1 text-sm font-medium text-pink-500 transition-all hover:gap-2"
        >
          <span>{t("videos.viewDetails")}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
});

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

  const statusOptions: { value: StatusFilter; label: string; className: string; emoji: string }[] =
    [
      {
        value: "all",
        label: t("videos.filterStatus.all"),
        className: "text-cloud-600 dark:text-cloud-300",
        emoji: "🌈",
      },
      {
        value: "completed",
        label: t("videos.filterStatus.completed"),
        className: "text-mint-600 dark:text-mint-300",
        emoji: "✨",
      },
      {
        value: "running",
        label: t("videos.filterStatus.running"),
        className: "text-sky-600 dark:text-sky-300",
        emoji: "🎬",
      },
      {
        value: "queued",
        label: t("videos.filterStatus.queued"),
        className: "text-amber-600 dark:text-amber-300",
        emoji: "⏳",
      },
      {
        value: "failed",
        label: t("videos.filterStatus.failed"),
        className: "text-pink-600 dark:text-pink-300",
        emoji: "💦",
      },
    ];

  return (
    <div className="relative z-10 mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-white/60 bg-white/60 p-4 shadow-md backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
      <div className="flex min-w-[200px] flex-1 items-center gap-2 rounded-full border-2 border-transparent bg-cloud-100 px-4 py-2 shadow-sm transition-all focus-within:border-pink-300 focus-within:bg-white focus-within:shadow-md dark:bg-slate-800">
        <Search size={16} className="shrink-0 text-pink-400" />
        <input
          type="text"
          placeholder={t("videos.searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="min-w-0 flex-1 bg-transparent text-sm text-cloud-800 outline-none placeholder:text-cloud-500 dark:text-cloud-100"
        />
        {searchQuery && (
          <button
            type="button"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pink-300 text-white transition-all hover:scale-110 hover:bg-pink-500"
            onClick={() => onSearchChange("")}
            aria-label={t("videos.clearSearch")}
          >
            <span>×</span>
          </button>
        )}
      </div>

      <button
        type="button"
        className={cn(
          "flex items-center gap-2 rounded-full border-2 px-4 py-2 text-sm font-medium transition-all",
          isExpanded
            ? "border-lavender-400 bg-gradient-to-r from-lavender-400 to-pink-400 text-white shadow-md"
            : "border-transparent bg-cloud-100 text-cloud-700 hover:border-lavender-300 hover:bg-lavender-50 dark:bg-slate-800 dark:text-cloud-200"
        )}
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-label={t("videos.filter")}
      >
        <Filter size={16} />
        <span>{t("videos.filter")}</span>
      </button>

      <div className="ml-auto flex items-center gap-1 text-sm font-medium text-cloud-500 dark:text-cloud-400">
        <span className="text-lg">📹</span>
        <span>{t("videos.resultCount", { count: resultCount })}</span>
      </div>

      {isExpanded && (
        <div className="flex w-full flex-wrap gap-2 border-t border-dashed border-pink-200 pt-3 dark:border-pink-900/30">
          {statusOptions.map((option) => (
            <button
              type="button"
              key={option.value}
              className={cn(
                "flex items-center gap-1 rounded-full border-2 px-4 py-2 text-sm font-semibold transition-all",
                statusFilter === option.value
                  ? "border-current bg-white shadow-sm dark:bg-slate-800"
                  : "border-transparent bg-cloud-100 text-cloud-700 hover:-translate-y-0.5 hover:border-pink-200 hover:bg-pink-50 hover:text-pink-600 dark:bg-slate-800 dark:text-cloud-200"
              )}
              onClick={() => onStatusChange(option.value)}
            >
              <span className={cn("text-base", option.className)}>{option.emoji}</span>
              <span className={statusFilter === option.value ? option.className : ""}>
                {option.label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CloudDecoration() {
  return (
    <>
      <div className="pointer-events-none absolute left-[5%] top-[5%] -z-10 animate-float text-4xl opacity-40">
        ☁️
      </div>
      <div className="pointer-events-none absolute right-[10%] top-[15%] -z-10 animate-float text-5xl opacity-40 [animation-delay:-3s]">
        ☁️
      </div>
      <div className="pointer-events-none absolute bottom-[20%] left-[3%] -z-10 animate-float text-3xl opacity-40 [animation-delay:-5s]">
        ☁️
      </div>
      <div className="pointer-events-none absolute right-[5%] top-[10%] -z-10 animate-twinkle text-2xl opacity-60">
        ✨
      </div>
      <div className="pointer-events-none absolute left-[15%] top-[25%] -z-10 animate-twinkle text-xl opacity-60 [animation-delay:-1s]">
        ✨
      </div>
      <div className="pointer-events-none absolute left-[30%] top-[8%] -z-10 animate-twinkle text-lg opacity-60 [animation-delay:-0.5s]">
        🌸
      </div>
    </>
  );
}

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

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (statusFilter !== "all") {
        const itemStatus = item.status.toLowerCase();
        if (statusFilter === "running" && !["running", "rendering"].includes(itemStatus)) {
          return false;
        }
        if (statusFilter !== "running" && itemStatus !== statusFilter) {
          return false;
        }
      }
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
    <div className="relative min-h-screen bg-gradient-to-b from-[#E8F4F8] via-[#F0F7FA] to-[#FFF8F0] px-4 py-6 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 sm:px-6 sm:py-8">
      <CloudDecoration />
      <ARIALiveRegion />

      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-pink-500">
              <span className="text-base">🎬</span>
              <span>{t("videos.page.eyebrow")}</span>
            </div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-cloud-800 dark:text-cloud-100 sm:text-3xl">
              {t("videos.page.title")}
              <span className="animate-bounce text-2xl">✨</span>
            </h1>
            <p className="text-sm text-cloud-500 dark:text-cloud-400">
              {t("videos.page.description")}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div
              className="flex rounded-xl border border-white/60 bg-white/60 p-1 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60"
              role="group"
              aria-label={t("videos.viewToggle")}
            >
              <button
                type="button"
                className={cn(
                  "flex h-11 w-11 items-center justify-center rounded-lg transition-all",
                  viewMode === "grid"
                    ? "bg-gradient-to-br from-pink-400 to-peach-400 text-white shadow-sm"
                    : "text-cloud-500 hover:bg-pink-50 hover:text-pink-500 dark:text-cloud-400 dark:hover:bg-pink-900/20"
                )}
                onClick={() => setViewMode("grid")}
                aria-label={t("videos.gridView")}
                aria-pressed={viewMode === "grid"}
              >
                <Grid3X3 size={18} />
              </button>
              <button
                type="button"
                className={cn(
                  "flex h-11 w-11 items-center justify-center rounded-lg transition-all",
                  viewMode === "list"
                    ? "bg-gradient-to-br from-pink-400 to-peach-400 text-white shadow-sm"
                    : "text-cloud-500 hover:bg-pink-50 hover:text-pink-500 dark:text-cloud-400 dark:hover:bg-pink-900/20"
                )}
                onClick={() => setViewMode("list")}
                aria-label={t("videos.listView")}
                aria-pressed={viewMode === "list"}
              >
                <List size={18} />
              </button>
            </div>
            <button
              type="button"
              className="flex items-center gap-2 rounded-full bg-gradient-to-r from-mint-400 to-sky-400 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-70"
              onClick={refresh}
              disabled={status === "loading"}
              aria-busy={status === "loading"}
            >
              {status === "loading" ? (
                <Loader2 size={18} className="animate-spin" />
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
          <div className="mb-5 flex items-center gap-2 rounded-xl border-2 border-pink-300 bg-pink-100 px-4 py-3 text-sm font-medium text-pink-600 dark:border-pink-900/30 dark:bg-pink-900/20 dark:text-pink-300">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {status === "loading" && items.length === 0 ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : filteredItems.length > 0 ? (
          <div
            className={
              viewMode === "grid"
                ? "grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
                : "flex flex-col gap-3"
            }
          >
            {viewMode === "grid"
              ? filteredItems.map((video) => <VideoGridCard key={video.task_id} video={video} />)
              : filteredItems.map((video) => <VideoListItem key={video.task_id} video={video} />)}
          </div>
        ) : (
          <div className="flex flex-col items-center rounded-2xl border border-white/60 bg-white/60 px-6 py-16 text-center shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="mb-4 text-5xl animate-float">🎭</div>
            <p className="text-lg font-semibold text-cloud-700 dark:text-cloud-200">
              {searchQuery || statusFilter !== "all"
                ? t("videos.noResults")
                : t("videos.noPlayable")}
            </p>
            <span className="text-sm text-cloud-500 dark:text-cloud-400">
              {searchQuery || statusFilter !== "all"
                ? t("videos.tryAdjustFilter")
                : t("videos.noPlayableHint")}
            </span>
          </div>
        )}
      </div>

      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
