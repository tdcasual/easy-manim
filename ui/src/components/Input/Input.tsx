/**
 * Input - 统一输入组件
 * 设计系统表单组件，支持多种变体和状态
 */
import {
  forwardRef,
  type ReactNode,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import styles from "./Input.module.css";

export type InputSize = "sm" | "md" | "lg";
export type InputVariant = "default" | "filled" | "outline" | "ghost";
export type InputColor = "default" | "pink" | "mint" | "sky" | "lavender"; // 🌸 Kawaii 粉彩色

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  inputSize?: InputSize;
  variant?: InputVariant;
  color?: InputColor; // 🌸 Kawaii 粉彩色
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

    return (
      <div className={`${styles.inputWrapper} ${fullWidth ? styles.fullWidth : ""} ${className}`}>
        {label && (
          <label htmlFor={inputId} className={styles.label}>
            {label}
          </label>
        )}
        <div
          className={`
            ${styles.inputContainer}
            ${styles[inputSize]}
            ${styles[variant]}
            ${color !== "default" ? styles[color] : ""}
            ${error ? styles.error : ""}
            ${rounded ? styles.rounded : ""}
          `}
        >
          {leftIcon && <span className={styles.leftIcon}>{leftIcon}</span>}
          <input
            ref={ref}
            id={inputId}
            className={styles.input}
            aria-invalid={!!error}
            aria-describedby={
              error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined
            }
            {...props}
          />
          {rightIcon && <span className={styles.rightIcon}>{rightIcon}</span>}
        </div>
        {helperText && !error && (
          <span id={`${inputId}-helper`} className={styles.helperText}>
            {helperText}
          </span>
        )}
        {error && (
          <span id={`${inputId}-error`} className={styles.errorText} role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

// Textarea 组件
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

    const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
      if (autoResize) {
        const target = e.currentTarget;
        target.style.height = "auto";
        target.style.height = `${target.scrollHeight}px`;
      }
      onInput?.(e);
    };

    return (
      <div className={`${styles.inputWrapper} ${fullWidth ? styles.fullWidth : ""} ${className}`}>
        {label && (
          <label htmlFor={textareaId} className={styles.label}>
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={`
            ${styles.textarea}
            ${styles[size]}
            ${styles[variant]}
            ${error ? styles.error : ""}
            ${rounded ? styles.rounded : ""}
          `}
          aria-invalid={!!error}
          aria-describedby={
            error ? `${textareaId}-error` : helperText ? `${textareaId}-helper` : undefined
          }
          onInput={handleInput}
          {...props}
        />
        {helperText && !error && (
          <span id={`${textareaId}-helper`} className={styles.helperText}>
            {helperText}
          </span>
        )}
        {error && (
          <span id={`${textareaId}-error`} className={styles.errorText} role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

// Select 组件
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

    return (
      <div className={`${styles.inputWrapper} ${fullWidth ? styles.fullWidth : ""} ${className}`}>
        {label && (
          <label htmlFor={selectId} className={styles.label}>
            {label}
          </label>
        )}
        <div
          className={`
            ${styles.selectContainer}
            ${styles[selectSize]}
            ${styles[variant]}
            ${error ? styles.error : ""}
            ${rounded ? styles.rounded : ""}
          `}
        >
          <select
            ref={ref}
            id={selectId}
            className={styles.select}
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
          </select>
        </div>
        {helperText && !error && (
          <span id={`${selectId}-helper`} className={styles.helperText}>
            {helperText}
          </span>
        )}
        {error && (
          <span id={`${selectId}-error`} className={styles.errorText} role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";

// Checkbox 组件
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
      <div className={`${styles.checkboxWrapper} ${className}`}>
        <label className={styles.checkboxLabel}>
          <input
            ref={(el) => {
              setIndeterminate(el);
              if (typeof ref === "function") {
                ref(el);
              } else if (ref) {
                ref.current = el;
              }
            }}
            id={checkboxId}
            type="checkbox"
            className={`${styles.checkbox} ${error ? styles.error : ""}`}
            aria-invalid={!!error}
            {...props}
          />
          <span className={styles.checkboxText}>
            {label && <span className={styles.checkboxTitle}>{label}</span>}
            {helperText && <span className={styles.checkboxHelper}>{helperText}</span>}
          </span>
        </label>
        {error && (
          <span className={styles.errorText} role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Checkbox.displayName = "Checkbox";

// Radio 组件
interface RadioProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ label, helperText, error, className = "", id, ...props }, ref) => {
    const radioId = id ?? `radio-${Math.random().toString(36).slice(2, 11)}`;

    return (
      <div className={`${styles.radioWrapper} ${className}`}>
        <label className={styles.radioLabel}>
          <input
            ref={ref}
            id={radioId}
            type="radio"
            className={`${styles.radio} ${error ? styles.error : ""}`}
            aria-invalid={!!error}
            {...props}
          />
          <span className={styles.radioText}>
            {label && <span className={styles.radioTitle}>{label}</span>}
            {helperText && <span className={styles.radioHelper}>{helperText}</span>}
          </span>
        </label>
        {error && (
          <span className={styles.errorText} role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Radio.displayName = "Radio";
