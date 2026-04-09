import {
  forwardRef,
  type ReactNode,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import {
  Input as UIInput,
  Textarea as UITextarea,
  Select as UISelect,
  Checkbox as UICheckbox,
  Radio as UIRadio,
} from "../ui/input";
import { cn } from "../../lib/utils";

export type InputSize = "sm" | "md" | "lg";
export type InputVariant = "default" | "filled" | "outline" | "ghost";
export type InputColor = "default" | "pink" | "mint" | "sky" | "lavender";

const colorRingMap: Record<InputColor, string> = {
  default: "",
  pink: "focus-visible:ring-pink-400",
  mint: "focus-visible:ring-mint-400",
  sky: "focus-visible:ring-sky-400",
  lavender: "focus-visible:ring-lavender-400",
};

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  inputSize?: InputSize;
  variant?: InputVariant;
  color?: InputColor;
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
  rounded?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      inputSize = "md",
      variant = "default",
      color = "default",
      label,
      helperText,
      error,
      leftIcon,
      rightIcon,
      fullWidth = false,
      rounded = false,
      className = "",
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id ?? `input-${Math.random().toString(36).slice(2, 11)}`;
    const sizeClass =
      inputSize === "sm" ? "h-8 text-xs" : inputSize === "lg" ? "h-12 text-base" : "h-10 text-sm";
    const variantClass =
      variant === "ghost"
        ? "border-transparent bg-transparent shadow-none"
        : variant === "filled"
          ? "bg-muted border-transparent"
          : "";

    return (
      <div className={cn("flex flex-col gap-1.5", fullWidth && "w-full", className)}>
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-foreground">
            {label}
          </label>
        )}
        <div className={cn("relative flex items-center", fullWidth && "w-full")}>
          {leftIcon && <span className="absolute left-3 text-muted-foreground">{leftIcon}</span>}
          <UIInput
            ref={ref}
            id={inputId}
            className={cn(
              sizeClass,
              variantClass,
              colorRingMap[color],
              rounded && "rounded-full",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              error && "border-destructive focus-visible:ring-destructive"
            )}
            aria-invalid={!!error}
            aria-describedby={
              error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined
            }
            {...props}
          />
          {rightIcon && <span className="absolute right-3 text-muted-foreground">{rightIcon}</span>}
        </div>
        {helperText && !error && (
          <span id={`${inputId}-helper`} className="text-xs text-muted-foreground">
            {helperText}
          </span>
        )}
        {error && (
          <span id={`${inputId}-error`} className="text-xs text-destructive" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  size?: InputSize;
  variant?: InputVariant;
  label?: string;
  helperText?: string;
  error?: string;
  fullWidth?: boolean;
  rounded?: boolean;
  autoResize?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      size = "md",
      variant = "default",
      label,
      helperText,
      error,
      fullWidth = false,
      rounded = false,
      autoResize = false,
      className = "",
      id,
      onInput,
      ...props
    },
    ref
  ) => {
    const textareaId = id ?? `textarea-${Math.random().toString(36).slice(2, 11)}`;
    const sizeClass = size === "sm" ? "text-xs" : size === "lg" ? "text-base" : "text-sm";
    const variantClass =
      variant === "ghost"
        ? "border-transparent bg-transparent shadow-none"
        : variant === "filled"
          ? "bg-muted border-transparent"
          : "";

    const handleInput = (e: React.InputEvent<HTMLTextAreaElement>) => {
      if (autoResize) {
        const target = e.currentTarget;
        target.style.height = "auto";
        target.style.height = `${target.scrollHeight}px`;
      }
      onInput?.(e);
    };

    return (
      <div className={cn("flex flex-col gap-1.5", fullWidth && "w-full", className)}>
        {label && (
          <label htmlFor={textareaId} className="text-sm font-medium text-foreground">
            {label}
          </label>
        )}
        <UITextarea
          ref={ref}
          id={textareaId}
          className={cn(
            sizeClass,
            variantClass,
            rounded && "rounded-3xl",
            error && "border-destructive focus-visible:ring-destructive"
          )}
          aria-invalid={!!error}
          aria-describedby={
            error ? `${textareaId}-error` : helperText ? `${textareaId}-helper` : undefined
          }
          onInput={handleInput}
          {...props}
        />
        {helperText && !error && (
          <span id={`${textareaId}-helper`} className="text-xs text-muted-foreground">
            {helperText}
          </span>
        )}
        {error && (
          <span id={`${textareaId}-error`} className="text-xs text-destructive" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

interface SelectProps extends Omit<InputHTMLAttributes<HTMLSelectElement>, "size"> {
  selectSize?: InputSize;
  variant?: InputVariant;
  label?: string;
  helperText?: string;
  error?: string;
  options: { value: string; label: string; disabled?: boolean }[];
  placeholder?: string;
  fullWidth?: boolean;
  rounded?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      selectSize = "md",
      variant = "default",
      label,
      helperText,
      error,
      options,
      placeholder,
      fullWidth = false,
      rounded = false,
      className = "",
      id,
      ...props
    },
    ref
  ) => {
    const selectId = id ?? `select-${Math.random().toString(36).slice(2, 11)}`;
    const sizeClass =
      selectSize === "sm" ? "h-8 text-xs" : selectSize === "lg" ? "h-12 text-base" : "h-10 text-sm";
    const variantClass =
      variant === "ghost"
        ? "border-transparent bg-transparent shadow-none"
        : variant === "filled"
          ? "bg-muted border-transparent"
          : "";

    return (
      <div className={cn("flex flex-col gap-1.5", fullWidth && "w-full", className)}>
        {label && (
          <label htmlFor={selectId} className="text-sm font-medium text-foreground">
            {label}
          </label>
        )}
        <UISelect
          ref={ref}
          id={selectId}
          className={cn(
            sizeClass,
            variantClass,
            rounded && "rounded-full",
            error && "border-destructive focus-visible:ring-destructive"
          )}
          aria-invalid={!!error}
          aria-describedby={
            error ? `${selectId}-error` : helperText ? `${selectId}-helper` : undefined
          }
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </UISelect>
        {helperText && !error && (
          <span id={`${selectId}-helper`} className="text-xs text-muted-foreground">
            {helperText}
          </span>
        )}
        {error && (
          <span id={`${selectId}-error`} className="text-xs text-destructive" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  indeterminate?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, helperText, error, indeterminate, className = "", id, ...props }, ref) => {
    const checkboxId = id ?? `checkbox-${Math.random().toString(36).slice(2, 11)}`;

    const setIndeterminate = (el: HTMLInputElement | null) => {
      if (el) {
        el.indeterminate = indeterminate ?? false;
      }
    };

    return (
      <div className={cn("flex flex-col gap-1", className)}>
        <label className="flex cursor-pointer items-start gap-3">
          <UICheckbox
            ref={(el) => {
              setIndeterminate(el);
              if (typeof ref === "function") {
                ref(el);
              } else if (ref) {
                ref.current = el;
              }
            }}
            id={checkboxId}
            className={cn("mt-0.5", error && "border-destructive")}
            aria-invalid={!!error}
            {...props}
          />
          <span className="flex flex-col">
            {label && <span className="text-sm font-medium text-foreground">{label}</span>}
            {helperText && <span className="text-xs text-muted-foreground">{helperText}</span>}
          </span>
        </label>
        {error && (
          <span className="text-xs text-destructive" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Checkbox.displayName = "Checkbox";

interface RadioProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ label, helperText, error, className = "", id, ...props }, ref) => {
    const radioId = id ?? `radio-${Math.random().toString(36).slice(2, 11)}`;

    return (
      <div className={cn("flex flex-col gap-1", className)}>
        <label className="flex cursor-pointer items-start gap-3">
          <UIRadio
            ref={ref}
            id={radioId}
            className={cn("mt-0.5", error && "border-destructive")}
            aria-invalid={!!error}
            {...props}
          />
          <span className="flex flex-col">
            {label && <span className="text-sm font-medium text-foreground">{label}</span>}
            {helperText && <span className="text-xs text-muted-foreground">{helperText}</span>}
          </span>
        </label>
        {error && (
          <span className="text-xs text-destructive" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Radio.displayName = "Radio";
