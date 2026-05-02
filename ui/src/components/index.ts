// Component exports - design system unified entry

// ================================
// Base components
// ================================

// Toast notifications
export { ToastProvider } from "./Toast";
export { useToast } from "./useToast";
export type { ToastType } from "./ToastContext";
export { useARIAMessage } from "./useARIAMessage";
export { useConfirm } from "./useConfirm";

// Auth
export { AuthModal, useAuthGuard } from "./AuthModal";

// Buttons
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

// Inputs
export { Input, Textarea, Select, Checkbox, Radio } from "./Input/Input";
export type { InputSize, InputVariant } from "./Input/Input";

// KawaiiIcon
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
// Visual components
// ================================

// Gradient backgrounds
export {
  GradientBackground,
  DreamyBackground,
  SunsetBackground,
  OceanBackground,
  MinimalBackground,
} from "./GradientBackground";

// Kawaii tags
export { KawaiiTag, StatusTag, DecorativeTag, CountTag, TagGroup } from "./KawaiiTag";
export type { TagVariant, TagSize } from "./KawaiiTag";

// Kawaii decorations
export {
  FloatingClouds,
  TwinklingStars,
  FallingPetals,
  FloatingBubbles,
  GradientOrbs,
  KawaiiBackground,
  KawaiiPageWrapper,
} from "./KawaiiDecorations";

// Animation containers
export {
  AnimatedContainer,
  StaggeredList,
  PageTransition,
  HoverAnimation,
  GlowEffect,
  Sparkle,
} from "./AnimatedContainer";
export type { AnimationType } from "./AnimatedContainer";

// ================================
// Existing components
// ================================

export { ErrorBoundary, ErrorFallback } from "./ErrorBoundary";
export { ARIALiveRegion } from "./ARIALiveRegion";
export { LocaleToggle } from "./LocaleToggle";
export { Skeleton, PageSkeleton, SkeletonCard, SkeletonMetricCard } from "./Skeleton";
export { ConfirmDialog } from "./ConfirmDialog";
export { DialogShell } from "./DialogShell/DialogShell";
export type { DialogShellProps } from "./DialogShell/DialogShell";
