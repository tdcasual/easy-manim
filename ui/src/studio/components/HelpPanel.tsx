/**
 * HelpPanel - 快捷键帮助面板
 * Kawaii 二次元风格
 */
import { useEffect, useRef } from "react";
import { EmojiIcon } from "../../components";
import styles from "../styles/HelpPanel.module.css";

interface HelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const shortcuts = [
  { key: "/", description: "聚焦输入框", emoji: "🔍" },
  { key: "Enter", description: "提交生成", emoji: "🚀" },
  { key: "Shift + Enter", description: "换行", emoji: "↩️" },
  { key: "Esc", description: "关闭面板/取消聚焦", emoji: "🚪" },
  { key: "H", description: "打开历史记录", emoji: "📚" },
  { key: "S", description: "打开设置", emoji: "⚙️" },
  { key: "T", description: "切换主题", emoji: "🌓" },
  { key: "?", description: "显示/隐藏帮助", emoji: "❓" },
];

export function HelpPanel({ isOpen, onClose }: HelpPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // ESC 关闭 - 只在面板打开时监听
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

  // 点击外部关闭 - 只在面板打开时监听
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div className={styles.overlay} onClick={onClose} />

      {/* 面板 */}
      <div ref={panelRef} className={styles.panel} role="dialog" aria-label="快捷键帮助">
        {/* 头部 */}
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <EmojiIcon emoji="⌨️" color="sky" size="sm" />
            <h2>快捷键</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭帮助"
            className={styles.closeButton}
          >
            <EmojiIcon emoji="✖️" color="white" size="xs" />
          </button>
        </div>

        {/* 快捷键列表 */}
        <div className={styles.shortcutList}>
          {shortcuts.map((shortcut, index) => (
            <div key={index} className={styles.shortcutItem}>
              <div className={styles.shortcutDesc}>
                <EmojiIcon emoji={shortcut.emoji} color="white" size="xs" />
                <span>{shortcut.description}</span>
              </div>
              <kbd className={styles.kbd}>{shortcut.key}</kbd>
            </div>
          ))}
        </div>

        {/* 底部提示 */}
        <div className={styles.footer}>
          <p>💡 提示：在输入框内按 Esc 可取消聚焦</p>
        </div>
      </div>
    </>
  );
}
