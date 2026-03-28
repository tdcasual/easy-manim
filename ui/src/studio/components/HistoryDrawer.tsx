/**
 * HistoryDrawer - 历史记录抽屉
 * Kawaii 二次元风格
 */
import { useEffect, useRef } from "react";
import { Play } from "lucide-react";
import { resolveApiUrl } from "../../lib/api";
import { EmojiIcon, KawaiiIcon } from "../../components";
import styles from "../styles/HistoryDrawer.module.css";

interface HistoryItem {
  id: string;
  title: string;
  status: "completed" | "running" | "queued" | "failed";
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
  completed: { emoji: "✨", label: "已完成", color: "mint" as const },
  running: { emoji: "🎬", label: "进行中", color: "sky" as const },
  queued: { emoji: "⏳", label: "排队中", color: "peach" as const },
  failed: { emoji: "💥", label: "失败", color: "pink" as const },
};

// 验证 URL 安全性
function isValidImageUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}

export function HistoryDrawer({
  isOpen,
  onClose,
  items,
  onItemClick,
  activeId,
}: HistoryDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousOverflowRef = useRef("");

  // 处理 ESC 关闭 - 只在 drawer 打开时监听
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // 处理点击外部关闭 + 背景滚动控制
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    previousOverflowRef.current = document.body.style.overflow;
    document.addEventListener("mousedown", handleClickOutside);
    document.body.style.overflow = "hidden";
    // 聚焦到关闭按钮
    closeButtonRef.current?.focus();

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.body.style.overflow = previousOverflowRef.current;
    };
  }, [isOpen, onClose]);

  // 焦点管理 (Tab 循环)
  useEffect(() => {
    if (!isOpen) return;

    const drawer = drawerRef.current;
    if (!drawer) return;

    const getFocusableElements = () => {
      return Array.from(
        drawer.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
    };

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;

      const focusableElements = getFocusableElements();
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };

    drawer.addEventListener("keydown", handleTabKey);
    return () => drawer.removeEventListener("keydown", handleTabKey);
  }, [isOpen]);

  return (
    <>
      {/* 遮罩 */}
      <div
        className={isOpen ? styles.overlay : styles.overlayHidden}
        onClick={onClose}
        aria-hidden={!isOpen}
      />

      {/* 抽屉 */}
      <div
        ref={drawerRef}
        className={isOpen ? styles.drawerOpen : styles.drawer}
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
              <h2 id="drawer-title">创作历史</h2>
              <p>🎨 {items.length} 个作品</p>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="关闭历史抽屉"
            className={styles.closeButton}
          >
            <EmojiIcon emoji="✖️" color="white" size="xs" />
          </button>
        </div>

        {/* 列表 */}
        <div className={styles.list} role="list" aria-label="创作历史列表">
          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <EmojiIcon emoji="📖" color="lavender" size="xl" bounce />
              </div>
              <p className={styles.emptyTitle}>还没有创作记录</p>
              <p className={styles.emptySubtitle}>开始创作你的第一个动画吧 ✨</p>
            </div>
          ) : (
            <div className={styles.items}>
              {items.map((item, index) => {
                const status = statusConfig[item.status];
                const isActive = item.id === activeId;
                const hasValidThumbnail = isValidImageUrl(item.thumbnailUrl);

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onItemClick(item.id)}
                    role="listitem"
                    aria-current={isActive ? "true" : undefined}
                    aria-label={`${item.title}, ${status.label}, ${item.timestamp}`}
                    className={isActive ? styles.itemActive : styles.item}
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    {/* 缩略图 */}
                    {hasValidThumbnail ? (
                      <div
                        className={styles.thumbnail}
                        style={{
                          background: `url(${resolveApiUrl(item.thumbnailUrl!)}) center/cover`,
                        }}
                        aria-hidden="true"
                      />
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
                          {status.label}
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
