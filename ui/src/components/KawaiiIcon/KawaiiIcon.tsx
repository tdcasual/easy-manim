import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

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

const sizeMap = {
  xs: 14,
  sm: 18,
  md: 22,
  lg: 28,
  xl: 36,
};

const colorClassMap: Record<IconColor, string> = {
  pink: "bg-gradient-to-br from-pink-400 to-pink-500 text-white shadow-[0_4px_12px_rgba(255,107,138,0.3)] hover:shadow-[0_6px_20px_rgba(255,107,138,0.5)]",
  mint: "bg-gradient-to-br from-mint-400 to-mint-500 text-white shadow-[0_4px_12px_rgba(77,179,144,0.3)] hover:shadow-[0_6px_20px_rgba(77,179,144,0.5)]",
  sky: "bg-gradient-to-br from-sky-400 to-sky-500 text-white shadow-[0_4px_12px_rgba(74,163,193,0.3)] hover:shadow-[0_6px_20px_rgba(74,163,193,0.5)]",
  lavender:
    "bg-gradient-to-br from-lavender-400 to-lavender-500 text-white shadow-[0_4px_12px_rgba(168,85,168,0.3)] hover:shadow-[0_6px_20px_rgba(168,85,168,0.5)]",
  peach:
    "bg-gradient-to-br from-peach-400 to-peach-500 text-white shadow-[0_4px_12px_rgba(244,140,75,0.3)] hover:shadow-[0_6px_20px_rgba(244,140,75,0.5)]",
  lemon:
    "bg-gradient-to-br from-lemon-400 to-lemon-500 text-white shadow-[0_4px_12px_rgba(242,214,64,0.34)]",
  white:
    "bg-gradient-to-br from-white to-cloud-300 text-cloud-700 shadow-sm dark:from-cloud-300 dark:to-cloud-400 dark:text-cloud-100",
  gradient:
    "bg-gradient-to-br from-pink-400 via-mint-400 to-sky-400 text-white shadow-[0_4px_16px_rgba(255,167,196,0.4)]",
};

const sizeClassMap: Record<IconSize, string> = {
  xs: "h-6 w-6 text-sm",
  sm: "h-8 w-8 text-lg",
  md: "h-10 w-10 text-[22px]",
  lg: "h-[52px] w-[52px] text-[28px]",
  xl: "h-16 w-16 text-4xl",
};

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
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full transition-all duration-300",
        colorClassMap[color],
        sizeClassMap[size],
        pulse && "animate-pulse-glow",
        bounce && "animate-bounce-kawaii",
        rotate && "animate-spin-slow",
        onClick && "cursor-pointer min-h-11 min-w-11 hover:scale-120 active:scale-95",
        !onClick && "hover:scale-115 hover:rotate-[5deg]",
        className
      )}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <Icon size={sizeMap[size]} strokeWidth={2.5} />
    </span>
  );
}

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
      className={cn(
        "inline-flex items-center justify-center rounded-full leading-none transition-all duration-300",
        colorClassMap[color],
        sizeClassMap[size],
        pulse && "animate-pulse-glow",
        bounce && "animate-bounce-kawaii",
        "hover:scale-115 hover:rotate-[5deg]",
        className
      )}
    >
      {emoji}
    </span>
  );
}

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
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full border-none text-white transition-all duration-300 hover:scale-115 hover:rotate-[10deg] active:scale-95",
        colorClassMap[color],
        size === "xs" || size === "sm" || size === "md"
          ? "h-11 w-11"
          : size === "lg"
            ? "h-14 w-14"
            : "h-[68px] w-[68px]",
        className
      )}
      onClick={onClick}
      aria-label={ariaLabel}
      type="button"
    >
      <Icon size={sizeMap[size]} strokeWidth={2.5} />
    </button>
  );
}

interface IconGroupProps {
  children: ReactNode;
  className?: string;
}

export function IconGroup({ children, className = "" }: IconGroupProps) {
  return <span className={cn("inline-flex items-center gap-2", className)}>{children}</span>;
}

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
  return (
    <span
      className={cn("inline-block animate-float", className)}
      style={{ animationDelay: `${delay}s` }}
    >
      {emoji ? (
        <EmojiIcon emoji={emoji} color={color} size={size} bounce />
      ) : icon ? (
        <KawaiiIcon icon={icon} color={color} size={size} bounce />
      ) : null}
    </span>
  );
}
