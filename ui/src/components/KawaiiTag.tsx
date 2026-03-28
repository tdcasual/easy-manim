/**
 * KawaiiTag - 二次元风格标签组件
 * 可爱、柔和、有弹性的标签设计
 */
import type { ReactNode } from "react";
import "./KawaiiTag.css";

export type TagVariant =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "pink"
  | "mint"
  | "sky"
  | "lavender"
  | "peach"
  | "purple" // 兼容旧命名
  | "cyan" // 兼容旧命名
  | "orange"; // 兼容旧命名

export type TagSize = "sm" | "md" | "lg";

interface KawaiiTagProps {
  children: ReactNode;
  variant?: TagVariant;
  size?: TagSize;
  icon?: ReactNode;
  closable?: boolean;
  onClose?: () => void;
  pulse?: boolean;
  className?: string;
}

export function KawaiiTag({
  children,
  variant = "default",
  size = "md",
  icon,
  closable = false,
  onClose,
  pulse = false,
  className = "",
}: KawaiiTagProps) {
  return (
    <span
      className={`kawaii-tag ${variant} ${size} ${pulse ? "pulse" : ""} ${closable ? "closable" : ""} ${className}`}
    >
      {icon && <span className="tag-icon">{icon}</span>}
      <span className="tag-content">{children}</span>
      {closable && (
        <button
          type="button"
          className="tag-close"
          onClick={(e) => {
            e.stopPropagation();
            onClose?.();
          }}
          aria-label="移除标签"
        >
          ×
        </button>
      )}
    </span>
  );
}

// 状态标签 - 带图标和动画
interface StatusTagProps {
  status: "running" | "completed" | "failed" | "queued" | "cancelled" | "pending";
  children?: ReactNode;
  size?: TagSize;
}

const statusConfig = {
  running: {
    variant: "sky" as TagVariant, // 使用 sky 替代 cyan
    icon: "◌",
    pulse: true,
  },
  completed: {
    variant: "success" as TagVariant,
    icon: "✓",
    pulse: false,
  },
  failed: {
    variant: "error" as TagVariant,
    icon: "✕",
    pulse: false,
  },
  queued: {
    variant: "warning" as TagVariant,
    icon: "◷",
    pulse: false,
  },
  cancelled: {
    variant: "default" as TagVariant,
    icon: "-",
    pulse: false,
  },
  pending: {
    variant: "info" as TagVariant,
    icon: "◌",
    pulse: true,
  },
};

export function StatusTag({ status, children, size = "md" }: StatusTagProps) {
  const config = statusConfig[status];
  return (
    <KawaiiTag
      variant={config.variant}
      size={size}
      icon={<span className="status-icon-symbol">{config.icon}</span>}
      pulse={config.pulse}
    >
      {children ?? status}
    </KawaiiTag>
  );
}

// 装饰性标签 - 带表情符号
interface DecorativeTagProps {
  emoji: string;
  children: ReactNode;
  color?: "pink" | "yellow" | "blue" | "green" | "purple";
}

export function DecorativeTag({ emoji, children, color = "pink" }: DecorativeTagProps) {
  const colorVariant: Record<string, TagVariant> = {
    pink: "pink",
    yellow: "warning",
    blue: "info",
    green: "success",
    purple: "purple",
  };

  return (
    <KawaiiTag variant={colorVariant[color]} size="md" icon={emoji}>
      {children}
    </KawaiiTag>
  );
}

// 计数标签 - 带数字角标
interface CountTagProps {
  count: number;
  max?: number;
  children: ReactNode;
  variant?: TagVariant;
}

export function CountTag({ count, max = 99, children, variant = "primary" }: CountTagProps) {
  const displayCount = count > max ? `${max}+` : count;

  return (
    <span className="kawaii-count-tag">
      <KawaiiTag variant={variant} size="md">
        {children}
      </KawaiiTag>
      {count > 0 && <span className="count-badge">{displayCount}</span>}
    </span>
  );
}

// 标签组 - 可折叠
interface TagGroupProps {
  tags: { id: string; label: string; variant?: TagVariant }[];
  maxVisible?: number;
  size?: TagSize;
}

export function TagGroup({ tags, maxVisible = 3, size = "sm" }: TagGroupProps) {
  const visibleTags = tags.slice(0, maxVisible);
  const remainingCount = tags.length - maxVisible;

  return (
    <div className="kawaii-tag-group">
      {visibleTags.map((tag) => (
        <KawaiiTag key={tag.id} variant={tag.variant ?? "default"} size={size}>
          {tag.label}
        </KawaiiTag>
      ))}
      {remainingCount > 0 && (
        <KawaiiTag variant="default" size={size}>
          +{remainingCount}
        </KawaiiTag>
      )}
    </div>
  );
}
