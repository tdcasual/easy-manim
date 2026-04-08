/**
 * HelpPanel - 快捷键帮助面板
 * Kawaii 二次元风格
 */
import { useRef } from "react";
import { useI18n } from "../../app/locale";
import { EmojiIcon } from "../../components";
import { DialogShell } from "../../components/DialogShell/DialogShell";
import styles from "../styles/HelpPanel.module.css";

interface HelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpPanel({ isOpen, onClose }: HelpPanelProps) {
  const { t } = useI18n();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const shortcuts = [
    { key: "/", description: t("studio.help.shortcuts.focusPrompt"), emoji: "🔍" },
    { key: "Enter", description: t("studio.help.shortcuts.submit"), emoji: "🚀" },
    { key: "Shift + Enter", description: t("studio.help.shortcuts.newline"), emoji: "↩️" },
    { key: "Esc", description: t("studio.help.shortcuts.escape"), emoji: "🚪" },
    { key: "H", description: t("studio.help.shortcuts.history"), emoji: "📚" },
    { key: "S", description: t("studio.help.shortcuts.settings"), emoji: "⚙️" },
    { key: "T", description: t("studio.help.shortcuts.theme"), emoji: "🌓" },
    { key: "?", description: t("studio.help.shortcuts.help"), emoji: "❓" },
  ];

  return (
    <DialogShell
      isOpen={isOpen}
      onClose={onClose}
      dialogRef={panelRef}
      initialFocusRef={closeButtonRef}
      className={styles.panel}
      ariaLabel={t("studio.help.dialog")}
      overlayClassName={styles.overlay}
      overlayAriaLabel="Dismiss help panel backdrop"
    >
      {/* 头部 */}
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <EmojiIcon emoji="⌨️" color="sky" size="sm" />
          <h2>{t("studio.help.title")}</h2>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          onClick={onClose}
          aria-label={t("studio.help.close")}
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
        <p>💡 {t("studio.help.footer")}</p>
      </div>
    </DialogShell>
  );
}
