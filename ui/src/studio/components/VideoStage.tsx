import { useRef, useState, useCallback, useEffect } from "react";
import { useI18n } from "../../app/locale";
import { resolveApiUrl } from "../../lib/api";
import { cn } from "../../lib/utils";

interface VideoStageProps {
  videoUrl?: string | null;
  posterUrl?: string | null;
  isGenerating?: boolean;
  title?: string;
  compact?: boolean;
  onPlay?: () => void;
  onPause?: () => void;
  onCancel?: () => void;
}

// 进度条组件
function ProgressBar({ progress }: { progress: number }) {
  const clamped = Math.min(100, Math.max(0, progress));
  return (
    <div className="flex w-full max-w-xs items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-cloud-200">
        <div
          className="h-full rounded-full bg-gradient-to-r from-pink-400 to-mint-400 transition-all"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="w-10 text-right text-sm font-medium text-cloud-600">
        {Math.round(clamped)}%
      </div>
    </div>
  );
}

// 生成中动画
function GeneratingAnimation({ onCancel }: { onCancel?: () => void }) {
  const { t } = useI18n();
  const [progress, setProgress] = useState(0);
  const [timeLeft, setTimeLeft] = useState(30);

  useEffect(() => {
    const start = Date.now();
    const duration = 30000;

    const interval = setInterval(() => {
      const elapsed = Date.now() - start;
      const remaining = Math.max(0, duration - elapsed);

      const raw = Math.min(95, (elapsed / duration) * 100);
      const eased = raw < 50 ? raw * 1.2 : 50 + (raw - 50) * 0.6;

      setProgress(Math.min(95, eased));
      setTimeLeft(Math.ceil(remaining / 1000));
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center gap-5 text-center">
      <div className="relative">
        <svg
          width="80"
          height="80"
          viewBox="0 0 80 80"
          fill="none"
          className="animate-bounce-kawaii"
        >
          <path d="M20 60L30 30L50 25L55 45L30 55L20 60Z" fill="var(--color-pink-300)" />
          <path d="M50 25L55 45L65 35L55 15L50 25Z" fill="var(--color-peach-300)" />
          <circle cx="25" cy="57" r="3" fill="var(--color-mint-300)" />
        </svg>
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-lg font-semibold text-foreground">{t("studio.video.generatingTitle")}</p>
        <p className="text-sm text-muted-foreground">{t("studio.video.generatingSubtitle")}</p>
        <p className="text-xs text-cloud-600">
          {t("studio.video.generatingEta", { seconds: timeLeft })}
        </p>
      </div>

      <ProgressBar progress={progress} />

      <div className="flex gap-2">
        <div
          className="h-2 w-2 animate-bounce rounded-full bg-pink-400"
          style={{ animationDelay: "0s" }}
        />
        <div
          className="h-2 w-2 animate-bounce rounded-full bg-mint-400"
          style={{ animationDelay: "0.2s" }}
        />
        <div
          className="h-2 w-2 animate-bounce rounded-full bg-sky-400"
          style={{ animationDelay: "0.4s" }}
        />
      </div>

      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-2 rounded-full border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm font-medium text-destructive transition-all hover:bg-destructive/20"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
          {t("studio.video.cancel")}
        </button>
      )}
    </div>
  );
}

// 空状态
function EmptyState({ compact = false }: { compact?: boolean }) {
  const { t } = useI18n();

  return (
    <div className={cn("flex flex-col items-center text-center", compact ? "gap-2.5" : "gap-4")}>
      <div
        className={cn(
          "flex items-center justify-center rounded-full bg-gradient-to-br from-pink-200 to-lavender-200 text-pink-600 shadow-md",
          compact ? "h-12 w-12" : "h-16 w-16"
        )}
      >
        <svg
          width={compact ? "24" : "32"}
          height={compact ? "24" : "32"}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M12 3l1.912 5.813a2 2 0 001.272 1.272L21 12l-5.813 1.912a2 2 0 00-1.272 1.272L12 21l-1.912-5.813a2 2 0 00-1.272-1.272L3 12l5.813-1.912a2 2 0 001.272-1.272L12 3z" />
        </svg>
      </div>
      <div className="flex flex-col gap-1">
        <p className={cn("font-semibold text-foreground", compact ? "text-sm" : "text-base")}>
          {t("studio.video.emptyTitle")}
        </p>
        <p className={cn("text-muted-foreground", compact ? "text-xs" : "text-sm")}>
          {t("studio.video.emptySubtitle")}
        </p>
      </div>
    </div>
  );
}

// 角落装饰
function CornerDecoration({ position }: { position: "tl" | "tr" | "bl" | "br" }) {
  const posClass = {
    tl: "left-3 top-3 rounded-br-xl",
    tr: "right-3 top-3 rounded-bl-xl",
    bl: "bottom-3 left-3 rounded-tr-xl",
    br: "bottom-3 right-3 rounded-tl-xl",
  }[position];

  return (
    <div
      className={cn("absolute h-6 w-6 border-2 border-pink-300/40", posClass)}
      aria-hidden="true"
    />
  );
}

export function VideoStage({
  videoUrl,
  posterUrl,
  isGenerating = false,
  title,
  compact = false,
  onPlay,
  onPause,
  onCancel,
}: VideoStageProps) {
  const { t } = useI18n();
  const videoRef = useRef<HTMLVideoElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const resolvedVideoUrl = videoUrl ? resolveApiUrl(videoUrl) : undefined;
  const resolvedPosterUrl = posterUrl ? resolveApiUrl(posterUrl) : undefined;

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    setIsPlaying(!video.paused);

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);

    return () => {
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.pause();
      video.removeAttribute("src");
      video.load();
    };
  }, [resolvedVideoUrl]);

  useEffect(() => {
    const stage = stageRef.current;
    return () => {
      if (document.fullscreenElement && stage?.contains(document.fullscreenElement)) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, []);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video
        .play()
        .then(() => onPlay?.())
        .catch(() => {});
    } else {
      video.pause();
      onPause?.();
    }
  }, [onPlay, onPause]);

  const toggleFullscreen = useCallback(async () => {
    if (!stageRef.current) return;
    try {
      if (!document.fullscreenElement) {
        await stageRef.current.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {
      // ignore fullscreen errors
    }
  }, []);

  return (
    <div
      ref={stageRef}
      className={cn(
        "relative flex w-full items-center justify-center overflow-hidden border-2 border-[var(--glass-border)] bg-[var(--glass-white)] p-1 shadow-lg backdrop-blur-xl",
        compact ? "max-w-full rounded-2xl" : "max-w-4xl rounded-3xl"
      )}
      role="region"
      aria-label={t("studio.video.regionLabel")}
      data-stage-layout={compact ? "compact" : "default"}
    >
      <div
        className={cn(
          "absolute inset-0 border-2 border-pink-200/30",
          compact ? "rounded-2xl" : "rounded-3xl"
        )}
        aria-hidden="true"
      />

      {!compact && (
        <>
          <CornerDecoration position="tl" />
          <CornerDecoration position="tr" />
          <CornerDecoration position="bl" />
          <CornerDecoration position="br" />
        </>
      )}

      <div
        className={cn(
          "relative z-10 flex w-full items-center justify-center rounded-2xl",
          compact ? "min-h-56 p-4 sm:min-h-72 sm:p-6" : "min-h-72 p-6",
          resolvedVideoUrl ? "bg-black/5" : "bg-gradient-to-br from-pink-50/40 to-lavender-50/40"
        )}
      >
        {isGenerating ? (
          <GeneratingAnimation onCancel={onCancel} />
        ) : resolvedVideoUrl ? (
          <>
            <video
              ref={videoRef}
              src={resolvedVideoUrl}
              poster={resolvedPosterUrl ?? undefined}
              className="max-h-[min(30rem,50vh)] w-full rounded-xl object-contain"
              onEnded={() => setIsPlaying(false)}
              aria-label={title ?? t("studio.video.generatedLabel")}
            />

            <button
              type="button"
              onClick={togglePlay}
              aria-label={isPlaying ? t("studio.video.pause") : t("studio.video.play")}
              className="absolute left-1/2 top-1/2 flex h-14 w-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-pink-600 shadow-lg backdrop-blur-md transition-all hover:scale-110"
            >
              {isPlaying ? (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              )}
            </button>

            <button
              type="button"
              onClick={toggleFullscreen}
              aria-label={t("studio.video.fullscreen")}
              className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-full bg-white/80 text-cloud-700 shadow-sm backdrop-blur-sm transition-all hover:bg-white hover:text-pink-600"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
              </svg>
            </button>

            {title && (
              <div
                className="absolute bottom-4 left-4 max-w-[80%] truncate rounded-full bg-white/80 px-3 py-1 text-sm font-medium text-foreground shadow-sm backdrop-blur-sm"
                title={title}
              >
                {title}
              </div>
            )}
          </>
        ) : (
          <EmptyState compact={compact} />
        )}
      </div>
    </div>
  );
}
