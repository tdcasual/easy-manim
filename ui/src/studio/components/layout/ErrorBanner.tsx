/**
 * ErrorBanner - error banner component.
 * Kawaii anime style.
 */
import type { TaskError } from "../../store";
import { useI18n } from "../../../app/locale";
import { StatusIcon, EmojiIcon } from "../../../components";

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
      className={`flex items-center gap-3 rounded-2xl border px-4 py-3 shadow-sm ${
        isNetwork
          ? "border-sky-200 bg-sky-50 text-sky-800"
          : "border-red-200 bg-red-50 text-red-800"
      }`}
    >
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
          isNetwork ? "bg-sky-100 text-sky-600" : "bg-red-100 text-red-600"
        }`}
      >
        {isNetwork ? (
          <EmojiIcon emoji="📡" color="sky" size="sm" />
        ) : (
          <StatusIcon status="error" size="sm" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className={`text-sm font-semibold ${isNetwork ? "text-sky-800" : "text-red-800"}`}>
          {error.type === "network" && t("studio.error.network")}
          {error.type === "timeout" && t("studio.error.timeout")}
          {error.type === "generation" && t("studio.error.generation")}
          {error.type === "unknown" && t("studio.error.unknown")}
        </div>
        <div className="text-xs opacity-90 truncate">{error.message}</div>
      </div>

      <div className="flex items-center gap-2">
        {error.retryable && onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1 rounded-xl border border-cloud-200 bg-white px-3 py-1.5 text-xs font-medium shadow-sm transition-colors hover:bg-cloud-50"
          >
            <EmojiIcon emoji="🔄" color="white" size="xs" />
            {t("studio.error.retry")}
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          aria-label={t("studio.error.close")}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-cloud-200 bg-white text-sm shadow-sm transition-colors hover:bg-cloud-50"
        >
          <EmojiIcon emoji="✖️" color="white" size="xs" />
        </button>
      </div>
    </div>
  );
}
