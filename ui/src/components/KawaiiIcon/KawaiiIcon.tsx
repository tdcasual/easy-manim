/**
 * KawaiiIcon - 二次元风格图标组件
 * 为 Lucide 图标添加可爱包装：彩色背景、圆形容器、弹性动画
 */

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./KawaiiIcon.module.css";

export type IconColor =
  | "pink"
  | "mint"
  | "sky"
  | "lavender"
  | "peach"
  | "lemon"
  | "white"
  | "gradient";

export type IconSize = "xs" | "sm" | "md" | "lg" | "xl";

interface KawaiiIconProps {
  icon: LucideIcon;
  color?: IconColor;
  size?: IconSize;
  className?: string;
  pulse?: boolean;
  bounce?: boolean;
  rotate?: boolean;
  onClick?: () => void;
}

export function KawaiiIcon({
  icon: Icon,
  color = "pink",
  size = "md",
  className = "",
  pulse = false,
  bounce = false,
  rotate = false,
  onClick,
}: KawaiiIconProps) {
  const sizeMap = {
    xs: 14,
    sm: 18,
    md: 22,
    lg: 28,
    xl: 36,
  };

  return (
    <span
      className={`${styles.kawaiiIcon} ${styles[color]} ${styles[size]} ${
        pulse ? styles.pulse : ""
      } ${bounce ? styles.bounce : ""} ${rotate ? styles.rotate : ""} ${
        onClick ? styles.clickable : ""
      } ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <Icon size={sizeMap[size]} strokeWidth={2.5} />
    </span>
  );
}

// Emoji 图标组件 - 带彩色背景
interface EmojiIconProps {
  emoji: string;
  color?: IconColor;
  size?: IconSize;
  className?: string;
  pulse?: boolean;
  bounce?: boolean;
}

export function EmojiIcon({
  emoji,
  color = "pink",
  size = "md",
  className = "",
  pulse = false,
  bounce = false,
}: EmojiIconProps) {
  return (
    <span
      className={`${styles.emojiIcon} ${styles[color]} ${styles[size]} ${
        pulse ? styles.pulse : ""
      } ${bounce ? styles.bounce : ""} ${className}`}
    >
      {emoji}
    </span>
  );
}

// 图标按钮 - 可点击的图标
interface IconButtonProps {
  icon: LucideIcon;
  color?: IconColor;
  size?: IconSize;
  onClick: () => void;
  ariaLabel: string;
  className?: string;
}

export function KawaiiIconButton({
  icon: Icon,
  color = "white",
  size = "md",
  onClick,
  ariaLabel,
  className = "",
}: IconButtonProps) {
  const sizeMap = {
    xs: 14,
    sm: 18,
    md: 22,
    lg: 28,
    xl: 36,
  };

  return (
    <button
      className={`${styles.iconButton} ${styles[color]} ${styles[size]} ${className}`}
      onClick={onClick}
      aria-label={ariaLabel}
      type="button"
    >
      <Icon size={sizeMap[size]} strokeWidth={2.5} />
    </button>
  );
}

// 图标组 - 多个图标排列
interface IconGroupProps {
  children: ReactNode;
  className?: string;
}

export function IconGroup({ children, className = "" }: IconGroupProps) {
  return <span className={`${styles.iconGroup} ${className}`}>{children}</span>;
}

// 状态图标映射
interface StatusIconProps {
  status: "success" | "error" | "warning" | "info" | "loading";
  size?: IconSize;
  className?: string;
}

export function StatusIcon({ status, size = "md", className = "" }: StatusIconProps) {
  const statusConfig = {
    success: { emoji: "✨", color: "mint" as IconColor },
    error: { emoji: "💥", color: "pink" as IconColor },
    warning: { emoji: "⚠️", color: "peach" as IconColor },
    info: { emoji: "💡", color: "sky" as IconColor },
    loading: { emoji: "🌀", color: "lavender" as IconColor },
  };

  const config = statusConfig[status];
  return (
    <EmojiIcon
      emoji={config.emoji}
      color={config.color}
      size={size}
      className={className}
      pulse={status === "loading"}
    />
  );
}

// 装饰性浮动图标
interface FloatingIconProps {
  icon?: LucideIcon;
  emoji?: string;
  color?: IconColor;
  size?: IconSize;
  delay?: number;
  className?: string;
}

export function FloatingIcon({
  icon,
  emoji,
  color = "pink",
  size = "md",
  delay = 0,
  className = "",
}: FloatingIconProps) {
  if (emoji) {
    return (
      <span
        className={`${styles.floatingIcon} ${className}`}
        style={{ animationDelay: `${delay}s` }}
      >
        <EmojiIcon emoji={emoji} color={color} size={size} bounce />
      </span>
    );
  }

  if (icon) {
    return (
      <span
        className={`${styles.floatingIcon} ${className}`}
        style={{ animationDelay: `${delay}s` }}
      >
        <KawaiiIcon icon={icon} color={color} size={size} bounce />
      </span>
    );
  }

  return null;
}
