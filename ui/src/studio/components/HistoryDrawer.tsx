/**
 * HistoryDrawer - 历史记录抽屉
 * Kawaii 二次元风格
 */
import { useRef } from "react";
import { useI18n } from "../../app/locale";
import { getStatusLabel } from "../../app/ui";
import { Play } from "lucide-react";
import { resolveApiUrl } from "../../lib/api";
import { EmojiIcon, KawaiiIcon } from "../../components";
import { useDialogA11y } from "../../components/useDialogA11y";
import styles from "../styles/HistoryDrawer.module.css";

interface HistoryItem {
  id: string;
  title: string;
  status: "completed" | "running" | "rendering" | "queued" | "failed" | "cancelled";
  timestamp: string;
  thumbnailUrl?: string | null;
}

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: HistoryItem[];
  onItemClick: (id: string) => void;
  activeId?: string;
}

// 状态配置
const statusConfig = {
  completed: { emoji: "✨", color: "mint" as const },
  rendering: { emoji: "🎨", color: "sky" as const },
  running: { emoji: "🎬", color: "sky" as const },
  queued: { emoji: "⏳", color: "peach" as const },
  failed: { emoji: "💥", color: "pink" as const },
  cancelled: { emoji: "🚫", color: "lemon" as const },
};

function resolveThumbnailUrl(url: string | null | undefined): string | null {
  const resolved = resolveApiUrl(url);
  if (!resolved) return null;

  try {
    const parsed = new URL(resolved, window.location.origin);
    return ["http:", "https:"].includes(parsed.protocol) ? resolved : null;
  } catch {
    return null;
  }
}

export function HistoryDrawer({
  isOpen,
  onClose,
  items,
  onItemClick,
  activeId,
}: HistoryDrawerProps) {
  const { locale, t } = useI18n();
  const drawerRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  useDialogA11y({
    isOpen,
    onClose,
    dialogRef: drawerRef,
    initialFocusRef: closeButtonRef,
  });

  if (!isOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div className={styles.overlay} onClick={onClose} aria-hidden="true" />

      {/* 抽屉 */}
      <div
        ref={drawerRef}
        className={styles.drawerOpen}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        {/* 头部 */}
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <div className={styles.headerIcon} aria-hidden="true">
              <EmojiIcon emoji="📚" color="pink" size="sm" />
            </div>
            <div className={styles.headerText}>
              <h2 id="drawer-title">{t("studio.history.title")}</h2>
              <p>🎨 {t("studio.history.count", { count: items.length })}</p>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label={t("studio.history.close")}
            className={styles.closeButton}
          >
            <EmojiIcon emoji="✖️" color="white" size="xs" />
          </button>
        </div>

        {/* 列表 */}
        <div className={styles.list} role="list" aria-label={t("studio.history.list")}>
          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <EmojiIcon emoji="📖" color="lavender" size="xl" bounce />
              </div>
              <p className={styles.emptyTitle}>{t("studio.history.emptyTitle")}</p>
              <p className={styles.emptySubtitle}>{t("studio.history.emptySubtitle")}</p>
            </div>
          ) : (
            <div className={styles.items}>
              {items.map((item, index) => {
                const status = statusConfig[item.status] ?? {
                  emoji: "📹",
                  color: "lavender" as const,
                };
                const statusLabel = getStatusLabel(item.status, locale);
                const isActive = item.id === activeId;
                const thumbnailUrl = resolveThumbnailUrl(item.thumbnailUrl);

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onItemClick(item.id)}
                    role="listitem"
                    aria-current={isActive ? "true" : undefined}
                    aria-label={`${item.title}, ${statusLabel}, ${item.timestamp}`}
                    className={isActive ? styles.itemActive : styles.item}
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    {/* 缩略图 */}
                    {thumbnailUrl ? (
                      <div className={styles.thumbnail} aria-hidden="true">
                        <img className={styles.thumbnailImage} src={thumbnailUrl} alt="" />
                      </div>
                    ) : (
                      <div className={styles.thumbnailPlaceholder} aria-hidden="true">
                        <KawaiiIcon icon={Play} color="white" size="xs" />
                      </div>
                    )}

                    {/* 信息 */}
                    <div className={styles.itemInfo}>
                      <p className={styles.itemTitle}>{item.title}</p>
                      <div className={styles.itemMeta}>
                        <span className={styles.status}>
                          <EmojiIcon emoji={status.emoji} color={status.color} size="xs" />
                          {statusLabel}
                        </span>
                        <span className={styles.timestamp}>{item.timestamp}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
