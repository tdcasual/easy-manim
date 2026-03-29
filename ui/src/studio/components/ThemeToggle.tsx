/**
 * ThemeToggle - 主题切换按钮
 * Kawaii 二次元风格 - 使用 emoji
 */
import { useI18n } from "../../app/locale";
import { EmojiIcon } from "../../components";
import styles from "../styles/ThemeToggle.module.css";

interface ThemeToggleProps {
  isNight: boolean;
  onToggle: () => void;
}

export function ThemeToggle({ isNight, onToggle }: ThemeToggleProps) {
  const { t } = useI18n();

  return (
    <button
      type="button"
      onClick={onToggle}
      className={isNight ? styles.toggleNight : styles.toggleDay}
      aria-label={isNight ? t("studio.theme.toDay") : t("studio.theme.toNight")}
      aria-pressed={isNight}
    >
      {/* 背景光晕 */}
      <div className={isNight ? styles.glowNight : styles.glowDay} aria-hidden="true" />

      {/* 图标 */}
      <div className={styles.icon} aria-hidden="true">
        {isNight ? (
          <EmojiIcon emoji="🌙" color="lavender" size="xs" />
        ) : (
          <EmojiIcon emoji="☀️" color="lemon" size="xs" />
        )}
      </div>
    </button>
  );
}
