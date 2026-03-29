/**
 * VideoStage - 视频展示舞台
 * 重构后版本 - 使用 CSS Modules
 */
import { useRef, useState, useCallback, useEffect } from "react";
import { useI18n } from "../../app/locale";
import { resolveApiUrl } from "../../lib/api";
import styles from "../styles/VideoStage.module.css";

interface VideoStageProps {
  videoUrl?: string | null;
  posterUrl?: string | null;
  isGenerating?: boolean;
  title?: string;
  onPlay?: () => void;
  onPause?: () => void;
  onCancel?: () => void;
}

// 进度条组件
function ProgressBar({ progress }: { progress: number }) {
  const clamped = Math.min(100, Math.max(0, progress));
  return (
    <div className={styles.progressBar}>
      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${clamped}%` }} />
      </div>
      <div className={styles.progressText}>{Math.round(clamped)}%</div>
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
    <div className={styles.generating}>
      <div className={styles.brushAnimation}>
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none" className={styles.brush}>
          <path d="M20 60L30 30L50 25L55 45L30 55L20 60Z" className={styles.brushPath1} />
          <path d="M50 25L55 45L65 35L55 15L50 25Z" className={styles.brushPath2} />
          <circle cx="25" cy="57" r="3" className={styles.brushTip} />
        </svg>
        <div className={styles.paintTrail} />
      </div>

      <div className={styles.generatingText}>
        <p className={styles.generatingTitle}>{t("studio.video.generatingTitle")}</p>
        <p className={styles.generatingSubtitle}>{t("studio.video.generatingSubtitle")}</p>
        <p className={styles.estimatedTime}>{t("studio.video.generatingEta", { seconds: timeLeft })}</p>
      </div>

      <ProgressBar progress={progress} />

      <div className={styles.dots}>
        <div className={styles.dot} />
        <div className={styles.dot} />
        <div className={styles.dot} />
      </div>

      {onCancel && (
        <button type="button" onClick={onCancel} className={styles.cancelButton}>
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
function EmptyState() {
  const { t } = useI18n();

  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>
        <svg
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M12 3l1.912 5.813a2 2 0 001.272 1.272L21 12l-5.813 1.912a2 2 0 00-1.272 1.272L12 21l-1.912-5.813a2 2 0 00-1.272-1.272L3 12l5.813-1.912a2 2 0 001.272-1.272L12 3z" />
        </svg>
      </div>
      <div className={styles.emptyText}>
        <p className={styles.emptyTitle}>{t("studio.video.emptyTitle")}</p>
        <p className={styles.emptySubtitle}>{t("studio.video.emptySubtitle")}</p>
      </div>
    </div>
  );
}

// 角落装饰
function CornerDecoration({ position }: { position: "tl" | "tr" | "bl" | "br" }) {
  const className = {
    tl: styles.cornerTopLeft,
    tr: styles.cornerTopRight,
    bl: styles.cornerBottomLeft,
    br: styles.cornerBottomRight,
  }[position];

  return <div className={`${styles.corner} ${className}`} aria-hidden="true" />;
}

export function VideoStage({
  videoUrl,
  posterUrl,
  isGenerating = false,
  title,
  onPlay,
  onPause,
  onCancel,
}: VideoStageProps) {
  const { t } = useI18n();
  const videoRef = useRef<HTMLVideoElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // 解析 URL
  const resolvedVideoUrl = videoUrl ? resolveApiUrl(videoUrl) : undefined;
  const resolvedPosterUrl = posterUrl ? resolveApiUrl(posterUrl) : undefined;

  // 同步视频状态 + 清理
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // 初始化播放状态
    setIsPlaying(!video.paused);

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);

    return () => {
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      // 暂停视频并清理 src 以防止内存泄漏
      video.pause();
      video.removeAttribute("src");
      video.load();
    };
  }, [resolvedVideoUrl]);

  // 组件卸载时退出全屏
  useEffect(() => {
    return () => {
      if (document.fullscreenElement && stageRef.current?.contains(document.fullscreenElement)) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, []);

  // 切换播放
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

  // 全屏
  const toggleFullscreen = useCallback(async () => {
    if (!stageRef.current) return;

    try {
      if (!document.fullscreenElement) {
        await stageRef.current.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {
      // 忽略不支持全屏的情况
    }
  }, []);

  return (
    <div ref={stageRef} className={styles.stage} role="region" aria-label={t("studio.video.regionLabel")}>
      <div className={styles.border} aria-hidden="true" />

      <CornerDecoration position="tl" />
      <CornerDecoration position="tr" />
      <CornerDecoration position="bl" />
      <CornerDecoration position="br" />

      <div
        className={`${styles.content} ${resolvedVideoUrl ? styles.contentVideo : styles.contentPlaceholder}`}
      >
        {isGenerating ? (
          <GeneratingAnimation onCancel={onCancel} />
        ) : resolvedVideoUrl ? (
          <>
            <video
              ref={videoRef}
              src={resolvedVideoUrl}
              poster={resolvedPosterUrl ?? undefined}
              className={styles.video}
              onEnded={() => setIsPlaying(false)}
              aria-label={title ?? t("studio.video.generatedLabel")}
            />

            <button
              type="button"
              onClick={togglePlay}
              aria-label={isPlaying ? t("studio.video.pause") : t("studio.video.play")}
              className={styles.playButton}
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
              className={styles.fullscreenButton}
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
              <div className={styles.title} title={title}>
                {title}
              </div>
            )}
          </>
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}
