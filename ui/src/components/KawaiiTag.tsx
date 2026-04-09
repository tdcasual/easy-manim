import type { ReactNode } from "react";
import { useI18n } from "../app/locale";
import { cn } from "../lib/utils";

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
  | "purple"
  | "cyan"
  | "orange";

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

const variantClassMap: Record<TagVariant, string> = {
  default:
    "bg-gradient-to-br from-cloud-200 to-cloud-300 border-cloud-400 text-cloud-700 dark:from-cloud-300 dark:to-cloud-400 dark:border-cloud-500 dark:text-cloud-100",
  primary:
    "bg-gradient-to-br from-mint-200 to-mint-300 border-mint-400 text-mint-700 dark:from-mint-300 dark:to-mint-400 dark:border-mint-500 dark:text-mint-100",
  secondary: "bg-gradient-to-br from-sky-200 to-sky-300 border-sky-400 text-sky-700",
  success: "bg-gradient-to-br from-green-200 to-green-300 border-green-400 text-green-700",
  warning: "bg-gradient-to-br from-amber-200 to-amber-300 border-amber-400 text-amber-700",
  error: "bg-gradient-to-br from-red-200 to-red-300 border-red-400 text-red-700",
  info: "bg-gradient-to-br from-blue-200 to-blue-300 border-blue-400 text-blue-700",
  pink: "bg-gradient-to-br from-pink-100 to-pink-200 border-pink-400 text-pink-700 dark:from-pink-300 dark:to-pink-400 dark:border-pink-500 dark:text-pink-100",
  mint: "bg-gradient-to-br from-mint-100 to-mint-200 border-mint-400 text-mint-700 dark:from-mint-300 dark:to-mint-400 dark:border-mint-500 dark:text-mint-100",
  sky: "bg-gradient-to-br from-sky-100 to-sky-200 border-sky-400 text-sky-700 dark:from-sky-300 dark:to-sky-400 dark:border-sky-500 dark:text-sky-100",
  lavender:
    "bg-gradient-to-br from-lavender-100 to-lavender-200 border-lavender-400 text-lavender-700 dark:from-lavender-300 dark:to-lavender-400 dark:border-lavender-500 dark:text-lavender-100",
  peach:
    "bg-gradient-to-br from-peach-100 to-peach-200 border-peach-400 text-peach-700 dark:from-peach-300 dark:to-peach-400 dark:border-peach-500 dark:text-peach-100",
  purple:
    "bg-gradient-to-br from-lavender-100 to-lavender-200 border-lavender-400 text-lavender-700 dark:from-lavender-300 dark:to-lavender-400 dark:border-lavender-500 dark:text-lavender-100",
  cyan: "bg-gradient-to-br from-sky-100 to-sky-200 border-sky-400 text-sky-700 dark:from-sky-300 dark:to-sky-400 dark:border-sky-500 dark:text-sky-100",
  orange:
    "bg-gradient-to-br from-peach-100 to-peach-200 border-peach-400 text-peach-700 dark:from-peach-300 dark:to-peach-400 dark:border-peach-500 dark:text-peach-100",
};

const sizeClassMap: Record<TagSize, string> = {
  sm: "px-2.5 py-1 text-[11px]",
  md: "px-3.5 py-1.5 text-[13px]",
  lg: "px-5 py-2.5 text-[15px]",
};

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
  const { t } = useI18n();

  return (
    <span
      className={cn(
        "inline-flex cursor-default select-none items-center gap-1.5 rounded-full border-2 border-transparent font-semibold transition-all duration-200",
        variantClassMap[variant],
        sizeClassMap[size],
        pulse && "animate-pulse-glow",
        closable && "pr-2",
        "shadow-sm hover:-translate-y-0.5 hover:shadow-md active:translate-y-0",
        className
      )}
    >
      {icon && <span className="flex items-center justify-center text-[1.1em]">{icon}</span>}
      <span>{children}</span>
      {closable && (
        <button
          type="button"
          className="relative ml-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full bg-black/10 text-inherit transition-all hover:scale-110 hover:bg-black/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current"
          onClick={(e) => {
            e.stopPropagation();
            onClose?.();
          }}
          aria-label={t("common.removeTag")}
        >
          <span className="text-sm font-bold leading-none">×</span>
        </button>
      )}
    </span>
  );
}

interface StatusTagProps {
  status: "running" | "completed" | "failed" | "queued" | "cancelled" | "pending";
  children?: ReactNode;
  size?: TagSize;
}

const statusConfig = {
  running: { variant: "sky" as TagVariant, icon: "◌", pulse: true },
  completed: { variant: "success" as TagVariant, icon: "✓", pulse: false },
  failed: { variant: "error" as TagVariant, icon: "✕", pulse: false },
  queued: { variant: "warning" as TagVariant, icon: "◷", pulse: false },
  cancelled: { variant: "default" as TagVariant, icon: "-", pulse: false },
  pending: { variant: "info" as TagVariant, icon: "◌", pulse: true },
};

export function StatusTag({ status, children, size = "md" }: StatusTagProps) {
  const config = statusConfig[status];
  return (
    <KawaiiTag
      variant={config.variant}
      size={size}
      icon={<span className="animate-pulse text-[0.9em]">{config.icon}</span>}
      pulse={config.pulse}
    >
      {children ?? status}
    </KawaiiTag>
  );
}

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
    purple: "lavender",
  };

  return (
    <KawaiiTag variant={colorVariant[color]} size="md" icon={emoji}>
      {children}
    </KawaiiTag>
  );
}

interface CountTagProps {
  count: number;
  max?: number;
  children: ReactNode;
  variant?: TagVariant;
}

export function CountTag({ count, max = 99, children, variant = "primary" }: CountTagProps) {
  const displayCount = count > max ? `${max}+` : count;

  return (
    <span className="relative inline-block">
      <KawaiiTag variant={variant} size="md">
        {children}
      </KawaiiTag>
      {count > 0 && (
        <span className="absolute -right-1.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full border-2 border-white bg-gradient-to-br from-red-400 to-red-600 px-1 text-[10px] font-bold leading-none text-white shadow-sm dark:border-card">
          {displayCount}
        </span>
      )}
    </span>
  );
}

interface TagGroupProps {
  tags: { id: string; label: string; variant?: TagVariant }[];
  maxVisible?: number;
  size?: TagSize;
}

export function TagGroup({ tags, maxVisible = 3, size = "sm" }: TagGroupProps) {
  const visibleTags = tags.slice(0, maxVisible);
  const remainingCount = tags.length - maxVisible;

  return (
    <div className="flex flex-wrap gap-2">
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
