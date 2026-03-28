/**
 * Button - 统一按钮组件
 * 设计系统基础组件，支持多种变体和尺寸
 */
import {
  forwardRef,
  type ReactNode,
  type ButtonHTMLAttributes,
  type AnchorHTMLAttributes,
} from "react";
import styles from "./Button.module.css";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "outline"
  | "ghost"
  | "danger"
  | "success"
  | "warning"
  | "info"
  | "pink"
  | "mint"
  | "sky"
  | "lavender"
  | "peach"; // 🌸 Kawaii 粉彩变体

export type ButtonSize = "xs" | "sm" | "md" | "lg" | "xl";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  iconPosition?: "left" | "right";
  fullWidth?: boolean;
  rounded?: boolean;
  elevation?: boolean;
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      iconPosition = "left",
      fullWidth = false,
      rounded = false,
      elevation = true,
      children,
      className = "",
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled ?? loading;

    return (
      <button
        ref={ref}
        className={`
          ${styles.button}
          ${styles[variant]}
          ${styles[size]}
          ${loading ? styles.loading : ""}
          ${fullWidth ? styles.fullWidth : ""}
          ${rounded ? styles.rounded : ""}
          ${elevation ? styles.elevation : ""}
          ${className}
        `}
        disabled={isDisabled}
        {...props}
      >
        {loading && (
          <span className={styles.spinner} aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray="60"
                strokeDashoffset="20"
              />
            </svg>
          </span>
        )}
        {!loading && icon && iconPosition === "left" && (
          <span className={styles.iconLeft}>{icon}</span>
        )}
        <span className={styles.content}>{children}</span>
        {!loading && icon && iconPosition === "right" && (
          <span className={styles.iconRight}>{icon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

// 图标按钮变体
interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  ariaLabel: string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    { icon, variant = "ghost", size = "md", loading = false, ariaLabel, className = "", ...props },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={`${styles.iconButton} ${styles[variant]} ${styles[size]} ${loading ? styles.loading : ""} ${className}`}
        aria-label={ariaLabel}
        disabled={props.disabled ?? loading}
        {...props}
      >
        {loading ? <span className={styles.spinnerSmall} aria-hidden="true" /> : icon}
      </button>
    );
  }
);

IconButton.displayName = "IconButton";

// 按钮组
interface ButtonGroupProps {
  children: ReactNode;
  attached?: boolean;
  className?: string;
}

export function ButtonGroup({ children, attached = false, className = "" }: ButtonGroupProps) {
  return (
    <div className={`${styles.buttonGroup} ${attached ? styles.attached : ""} ${className}`}>
      {children}
    </div>
  );
}

// 链接按钮（样式像按钮但实际是链接）
export interface LinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  iconPosition?: "left" | "right";
}

export const LinkButton = forwardRef<HTMLAnchorElement, LinkButtonProps>(
  (
    {
      href = "#",
      variant = "primary",
      size = "md",
      icon,
      iconPosition = "left",
      children,
      target,
      rel,
      ...props
    },
    ref
  ) => {
    const isExternal = target === "_blank";
    return (
      <a
        ref={ref}
        href={href}
        target={target}
        rel={isExternal ? "noopener noreferrer" : rel}
        className={`${styles.button} ${styles[variant]} ${styles[size]} ${styles.link}`}
        {...props}
      >
        {icon && iconPosition === "left" && <span className={styles.iconLeft}>{icon}</span>}
        <span className={styles.content}>{children}</span>
        {icon && iconPosition === "right" && <span className={styles.iconRight}>{icon}</span>}
      </a>
    );
  }
);

LinkButton.displayName = "LinkButton";

// 预设按钮快捷方式
export const PrimaryButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, "variant">>(
  (props, ref) => <Button ref={ref} variant="primary" {...props} />
);
PrimaryButton.displayName = "PrimaryButton";

export const SecondaryButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, "variant">>(
  (props, ref) => <Button ref={ref} variant="secondary" {...props} />
);
SecondaryButton.displayName = "SecondaryButton";

export const DangerButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, "variant">>(
  (props, ref) => <Button ref={ref} variant="danger" {...props} />
);
DangerButton.displayName = "DangerButton";

export const GhostButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, "variant">>(
  (props, ref) => <Button ref={ref} variant="ghost" {...props} />
);
GhostButton.displayName = "GhostButton";
