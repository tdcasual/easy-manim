/**
 * ChatInput - 对话式输入组件
 * 重构后版本 - 使用 CSS Modules
 */
import {
  useState,
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
  KeyboardEvent,
  useEffect,
} from "react";
import { useI18n } from "../../app/locale";
import styles from "../styles/ChatInput.module.css";

interface QuickPrompt {
  icon: string;
  text: string;
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
  placeholder?: string;
}

// 种子飞行动画
function SeedFlying({ isAnimating, onComplete }: { isAnimating: boolean; onComplete: () => void }) {
  if (!isAnimating) return null;

  return (
    <div className={styles.seedFlying}>
      <div className={styles.seed} onAnimationEnd={onComplete} />
    </div>
  );
}

export interface ChatInputRef {
  focus: () => void;
}

export const ChatInput = forwardRef<ChatInputRef, ChatInputProps>(
  ({ value, onChange, onSubmit, isLoading = false, placeholder }, ref) => {
    const { list, t } = useI18n();
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [isSeedFlying, setIsSeedFlying] = useState(false);
    const submitTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const quickPromptIcons = ["🔵", "📊", "📈"];
    const quickPrompts: QuickPrompt[] = list("studio.chat.quickPrompts").map((text, index) => ({
      icon: quickPromptIcons[index % quickPromptIcons.length],
      text,
    }));
    const resolvedPlaceholder = placeholder ?? t("studio.chat.placeholder");

    // 暴露 focus 方法给父组件
    useImperativeHandle(
      ref,
      () => ({
        focus: () => {
          textareaRef.current?.focus();
        },
      }),
      []
    );

    // 清理 timeout
    useEffect(() => {
      return () => {
        if (submitTimeoutRef.current) {
          clearTimeout(submitTimeoutRef.current);
        }
      };
    }, []);

    // 自动调整高度
    const adjustHeight = useCallback(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      textarea.style.height = "auto";
      const newHeight = Math.max(40, Math.min(textarea.scrollHeight, 150));
      textarea.style.height = `${newHeight}px`;
    }, []);

    // 内容变化时调整高度
    useEffect(() => {
      adjustHeight();
    }, [value, adjustHeight]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
    };

    const handleSubmit = () => {
      if (!value.trim() || isLoading) return;
      setIsSeedFlying(true);
      submitTimeoutRef.current = setTimeout(() => {
        onSubmit();
        submitTimeoutRef.current = null;
      }, 300);
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    };

    const handleQuickPrompt = (text: string) => {
      onChange(value ? `${value}, ${text}` : text);
      textareaRef.current?.focus();
    };

    return (
      <div className={styles.container}>
        {/* 快捷提示 */}
        <div className={styles.quickPrompts}>
          {quickPrompts.map((prompt, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleQuickPrompt(prompt.text)}
              className={styles.quickPromptCard}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <span className={styles.quickPromptIcon}>{prompt.icon}</span>
              <span>{prompt.text}</span>
            </button>
          ))}
        </div>

        {/* 输入框 */}
        <div className={styles.inputWrapper}>
          <div className={styles.topAccent} aria-hidden="true" />

          <div className={styles.inputContent}>
            {/* 左侧图标 */}
            <div
              className={`${styles.iconWrapper} ${!isLoading ? styles.iconWrapperAnimating : ""}`}
            >
              {isLoading ? (
                <div className={styles.spinner} />
              ) : (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M12 3l1.912 5.813a2 2 0 001.272 1.272L21 12l-5.813 1.912a2 2 0 00-1.272 1.272L12 21l-1.912-5.813a2 2 0 00-1.272-1.272L3 12l5.813-1.912a2 2 0 001.272-1.272L12 3z" />
                </svg>
              )}
            </div>

            {/* 文本域 */}
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder={isLoading ? t("studio.chat.loadingPlaceholder") : resolvedPlaceholder}
              disabled={isLoading}
              rows={1}
              className={styles.textarea}
              aria-label={t("studio.chat.label")}
              aria-busy={isLoading}
            />

            {/* 发送按钮 */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!value.trim() || isLoading}
              aria-label={isLoading ? t("studio.chat.sending") : t("studio.chat.send")}
              className={`${styles.sendButton} ${value.trim() && !isLoading ? styles.sendButtonActive : ""}`}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>

          <SeedFlying isAnimating={isSeedFlying} onComplete={() => setIsSeedFlying(false)} />
        </div>

        {/* 提示 */}
        <p className={styles.hint}>{t("studio.chat.hint")}</p>
      </div>
    );
  }
);

ChatInput.displayName = "ChatInput";
