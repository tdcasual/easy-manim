import {
  forwardRef,
  type ReactNode,
  type ButtonHTMLAttributes,
  type AnchorHTMLAttributes,
} from "react";
import { Button as UIButton } from "../ui/button";
import { buttonVariants } from "../ui/button-variants";
import { cn } from "../../lib/utils";
import type { VariantProps } from "class-variance-authority";

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
  | "peach";

export type ButtonSize = "xs" | "sm" | "md" | "lg" | "xl";

const variantMap: Record<ButtonVariant, VariantProps<typeof buttonVariants>["variant"]> = {
  primary: "default",
  secondary: "secondary",
  outline: "outline",
  ghost: "ghost",
  danger: "destructive",
  success: "mint",
  warning: "peach",
  info: "sky",
  pink: "pink",
  mint: "mint",
  sky: "sky",
  lavender: "lavender",
  peach: "peach",
};

const sizeMap: Record<ButtonSize, VariantProps<typeof buttonVariants>["size"]> = {
  xs: "sm",
  sm: "sm",
  md: "default",
  lg: "lg",
  xl: "lg",
};

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
    return (
      <UIButton
        ref={ref}
        variant={variantMap[variant]}
        size={sizeMap[size]}
        loading={loading}
        disabled={disabled ?? loading}
        className={cn(
          fullWidth && "w-full",
          rounded && "rounded-full",
          !elevation && "shadow-none hover:shadow-none",
          className
        )}
        {...props}
      >
        {!loading && icon && iconPosition === "left" && <span className="mr-1">{icon}</span>}
        {children}
        {!loading && icon && iconPosition === "right" && <span className="ml-1">{icon}</span>}
      </UIButton>
    );
  }
);

Button.displayName = "Button";

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
    const uiSize = sizeMap[size];
    const isIconSize = uiSize === "sm" ? "icon-sm" : uiSize === "lg" ? "icon-lg" : "icon";
    return (
      <UIButton
        ref={ref}
        variant={variantMap[variant]}
        size={isIconSize}
        loading={loading}
        aria-label={ariaLabel}
        className={className}
        disabled={props.disabled ?? loading}
        {...props}
      >
        {icon}
      </UIButton>
    );
  }
);

IconButton.displayName = "IconButton";

interface ButtonGroupProps {
  children: ReactNode;
  attached?: boolean;
  className?: string;
}

export function ButtonGroup({ children, attached = false, className = "" }: ButtonGroupProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2",
        attached &&
          "gap-0 [&>*:first-child]:rounded-r-none [&>*:last-child]:rounded-l-none [&>*:not(:first-child):not(:last-child)]:rounded-none",
        className
      )}
    >
      {children}
    </div>
  );
}

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
        className={cn(
          buttonVariants({ variant: variantMap[variant], size: sizeMap[size] }),
          "inline-flex"
        )}
        {...props}
      >
        {icon && iconPosition === "left" && <span className="mr-1">{icon}</span>}
        {children}
        {icon && iconPosition === "right" && <span className="ml-1">{icon}</span>}
      </a>
    );
  }
);

LinkButton.displayName = "LinkButton";

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
