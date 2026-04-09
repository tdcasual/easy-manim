import {
  useState,
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
  type KeyboardEvent,
  useEffect,
} from "react";
import { useI18n } from "../../app/locale";
import { cn } from "../../lib/utils";

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
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
      <div
        className="absolute bottom-6 right-12 h-3 w-3 rounded-full bg-gradient-to-br from-mint-300 to-sky-300 shadow-md"
        style={{ animation: "seedFly 0.6s ease-out forwards" }}
        onAnimationEnd={onComplete}
      />
      <style>{`
        @keyframes seedFly {
          0% { transform: translate(0, 0) scale(1); opacity: 1; }
          100% { transform: translate(120px, -80px) scale(0.5); opacity: 0; }
        }
      `}</style>
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

    useImperativeHandle(
      ref,
      () => ({
        focus: () => {
          textareaRef.current?.focus();
        },
      }),
      []
    );

    useEffect(() => {
      return () => {
        if (submitTimeoutRef.current) {
          clearTimeout(submitTimeoutRef.current);
        }
      };
    }, []);

    const adjustHeight = useCallback(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      textarea.style.height = "auto";
      const newHeight = Math.max(40, Math.min(textarea.scrollHeight, 150));
      textarea.style.height = `${newHeight}px`;
    }, []);

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
      <div className="flex flex-col gap-3">
        {/* 快捷提示 */}
        <div className="flex flex-wrap gap-2">
          {quickPrompts.map((prompt, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleQuickPrompt(prompt.text)}
              className="animate-float-in flex items-center gap-2 rounded-full border border-[var(--glass-border)] bg-[var(--glass-white)] px-3 py-1.5 text-sm text-cloud-700 shadow-xs backdrop-blur-md transition-all hover:-translate-y-0.5 hover:bg-gradient-to-br hover:from-pink-100 hover:to-lavender-100 hover:text-pink-600 hover:shadow-sm"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <span>{prompt.icon}</span>
              <span>{prompt.text}</span>
            </button>
          ))}
        </div>

        {/* 输入框 */}
        <div className="relative">
          <div
            className="absolute left-0 right-0 top-0 h-1 rounded-t-3xl bg-gradient-to-r from-pink-300 via-lavender-300 to-sky-300"
            aria-hidden="true"
          />

          <div className="flex items-center gap-3 rounded-3xl border-2 border-[var(--glass-border)] bg-[var(--glass-white)] p-3 shadow-md backdrop-blur-xl transition-all focus-within:border-pink-300 focus-within:shadow-lg">
            {/* 左侧图标 */}
            <div
              className={cn(
                "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full transition-all",
                isLoading
                  ? "bg-cloud-100 text-cloud-500"
                  : "bg-gradient-to-br from-pink-300 to-peach-300 text-white shadow-md animate-pulse-glow"
              )}
            >
              {isLoading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-cloud-300 border-t-cloud-600" />
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
              className="min-h-[40px] w-full resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
              aria-label={t("studio.chat.label")}
              aria-busy={isLoading}
            />

            {/* 发送按钮 */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!value.trim() || isLoading}
              aria-label={isLoading ? t("studio.chat.sending") : t("studio.chat.send")}
              className={cn(
                "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full transition-all",
                value.trim() && !isLoading
                  ? "bg-gradient-to-br from-mint-400 to-sky-400 text-white shadow-md hover:-translate-y-0.5 hover:shadow-lg"
                  : "bg-cloud-100 text-cloud-400"
              )}
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
        <p className="text-center text-xs text-cloud-600">{t("studio.chat.hint")}</p>
      </div>
    );
  }
);

ChatInput.displayName = "ChatInput";
