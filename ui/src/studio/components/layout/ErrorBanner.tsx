/**
 * ErrorBanner - 错误提示横幅
 * Kawaii 二次元风格
 */
import type { TaskError } from "../../store";
import { useI18n } from "../../../app/locale";
import { StatusIcon, EmojiIcon } from "../../../components";
import styles from "../../styles/Studio.module.css";

interface ErrorBannerProps {
  error: TaskError;
  onRetry?: () => void;
  onClose: () => void;
}

export function ErrorBanner({ error, onRetry, onClose }: ErrorBannerProps) {
  const { t } = useI18n();
  const isNetwork = error.type === "network";

  return (
    <div
      role="alert"
      className={`${styles.errorBanner} ${isNetwork ? styles.errorBannerNetwork : styles.errorBannerOther}`}
    >
      <div
        className={`${styles.errorIcon} ${isNetwork ? styles.errorIconNetwork : styles.errorIconOther}`}
      >
        {isNetwork ? (
          <EmojiIcon emoji="📡" color="sky" size="sm" />
        ) : (
          <StatusIcon status="error" size="sm" />
        )}
      </div>

      <div className={styles.errorContent}>
        <div
          className={`${styles.errorTitle} ${isNetwork ? styles.errorTitleNetwork : styles.errorTitleOther}`}
        >
          {error.type === "network" && t("studio.error.network")}
          {error.type === "timeout" && t("studio.error.timeout")}
          {error.type === "generation" && t("studio.error.generation")}
          {error.type === "unknown" && t("studio.error.unknown")}
        </div>
        <div className={styles.errorMessage}>{error.message}</div>
      </div>

      <div className={styles.errorActions}>
        {error.retryable && onRetry && (
          <button type="button" onClick={onRetry} className={styles.retryButton}>
            <EmojiIcon emoji="🔄" color="white" size="xs" />
            {t("studio.error.retry")}
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          aria-label={t("studio.error.close")}
          className={styles.closeButton}
        >
          <EmojiIcon emoji="✖️" color="white" size="xs" />
        </button>
      </div>
    </div>
  );
}
