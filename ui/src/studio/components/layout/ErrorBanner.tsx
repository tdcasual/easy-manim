/**
 * ErrorBanner - 错误提示横幅
 * Kawaii 二次元风格
 */
import type { TaskError } from "../../store";
import { StatusIcon, EmojiIcon } from "../../../components";
import styles from "../../styles/Studio.module.css";

interface ErrorBannerProps {
  error: TaskError;
  onRetry?: () => void;
  onClose: () => void;
}

export function ErrorBanner({ error, onRetry, onClose }: ErrorBannerProps) {
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
          {error.type === "network" && "网络错误"}
          {error.type === "timeout" && "请求超时"}
          {error.type === "generation" && "生成失败"}
          {error.type === "unknown" && "出错了"}
        </div>
        <div className={styles.errorMessage}>{error.message}</div>
      </div>

      <div className={styles.errorActions}>
        {error.retryable && onRetry && (
          <button type="button" onClick={onRetry} className={styles.retryButton}>
            <EmojiIcon emoji="🔄" color="white" size="xs" />
            重试
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭错误提示"
          className={styles.closeButton}
        >
          <EmojiIcon emoji="✖️" color="white" size="xs" />
        </button>
      </div>
    </div>
  );
}
