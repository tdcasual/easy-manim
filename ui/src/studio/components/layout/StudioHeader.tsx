/**
 * StudioHeader - Studio 头部组件
 * Kawaii 二次元风格
 */
import { Sparkles } from "lucide-react";
import { ThemeToggle } from "../ThemeToggle";
import { KawaiiIcon, EmojiIcon } from "../../../components";
import styles from "../../styles/Studio.module.css";

interface StudioHeaderProps {
  onOpenHistory: () => void;
  onOpenSettings: () => void;
  isNight: boolean;
  onToggleTheme: () => void;
}

export function StudioHeader({
  onOpenHistory,
  onOpenSettings,
  isNight,
  onToggleTheme,
}: StudioHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.logoSection}>
        <div className={styles.logo}>
          <KawaiiIcon icon={Sparkles} color="gradient" size="sm" pulse />
        </div>
        <div className={styles.brand}>
          <h1 className={styles.brandTitle}>easy-manim</h1>
          <p className={styles.brandSubtitle}>🎨 AI 动画创作室</p>
        </div>
      </div>

      <div className={styles.toolbar}>
        <button type="button" onClick={onOpenHistory} className={styles.toolbarButton}>
          <EmojiIcon emoji="📚" color="sky" size="xs" />
          <span>历史</span>
        </button>
        <button type="button" onClick={onOpenSettings} className={styles.toolbarButton}>
          <EmojiIcon emoji="⚙️" color="mint" size="xs" />
          <span>设置</span>
        </button>
        <div className={styles.toolbarDivider} />
        <div style={{ width: "4px" }} />
        <ThemeToggle isNight={isNight} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
