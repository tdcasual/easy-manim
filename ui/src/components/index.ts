// 组件导出 - 设计系统统一入口

// ================================
// 基础组件
// ================================

// Toast 通知
export { ToastProvider } from "./Toast";
export { useToast } from "./useToast";
export type { ToastType } from "./ToastContext";
export { useARIAMessage } from "./useARIAMessage";
export { useConfirm } from "./useConfirm";

// Auth 认证
export { AuthModal, useAuthGuard } from "./AuthModal";

// Button 按钮
export {
  Button,
  IconButton,
  ButtonGroup,
  LinkButton,
  PrimaryButton,
  SecondaryButton,
  DangerButton,
  GhostButton,
} from "./Button/Button";
export type { ButtonVariant, ButtonSize, ButtonProps, LinkButtonProps } from "./Button/Button";

// Input 输入
export { Input, Textarea, Select, Checkbox, Radio } from "./Input/Input";
export type { InputSize, InputVariant } from "./Input/Input";

// KawaiiIcon 二次元图标
export {
  KawaiiIcon,
  EmojiIcon,
  KawaiiIconButton,
  IconGroup,
  StatusIcon,
  FloatingIcon,
} from "./KawaiiIcon/KawaiiIcon";
export type { IconColor, IconSize } from "./KawaiiIcon/KawaiiIcon";

// ================================
// 视觉组件
// ================================

// 渐变背景
export {
  GradientBackground,
  DreamyBackground,
  SunsetBackground,
  OceanBackground,
  MinimalBackground,
} from "./GradientBackground";

// Kawaii 标签
export { KawaiiTag, StatusTag, DecorativeTag, CountTag, TagGroup } from "./KawaiiTag";
export type { TagVariant, TagSize } from "./KawaiiTag";

// Kawaii 装饰元素
export {
  FloatingClouds,
  TwinklingStars,
  FallingPetals,
  FloatingBubbles,
  GradientOrbs,
  KawaiiBackground,
  KawaiiPageWrapper,
} from "./KawaiiDecorations";

// 动画容器
export {
  AnimatedContainer,
  StaggeredList,
  PageTransition,
  HoverAnimation,
  FloatingElement,
  GlowEffect,
  Sparkle,
} from "./AnimatedContainer";
export type { AnimationType } from "./AnimatedContainer";

// ================================
// 现有组件
// ================================

export { ErrorBoundary, ErrorFallback } from "./ErrorBoundary";
export { ARIALiveRegion } from "./ARIALiveRegion";
export { LocaleToggle } from "./LocaleToggle";
export { Skeleton, PageSkeleton, SkeletonCard, SkeletonMetricCard } from "./Skeleton";
export { ConfirmDialog } from "./ConfirmDialog";
export { DialogShell } from "./DialogShell/DialogShell";
export type { DialogShellProps } from "./DialogShell/DialogShell";
