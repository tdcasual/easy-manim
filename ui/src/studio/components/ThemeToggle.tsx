import { useI18n } from "../../app/locale";
import { EmojiIcon } from "../../components";
import { cn } from "../../lib/utils";

interface ThemeToggleProps {
  isNight: boolean;
  onToggle: () => void;
}

export function ThemeToggle({ isNight, onToggle }: ThemeToggleProps) {
  const { t } = useI18n();

  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "relative flex h-10 w-10 items-center justify-center rounded-full border border-cloud-200 bg-white shadow-xs transition-transform transition-shadow duration-300 hover:-translate-y-0.5 hover:shadow-md dark:border-cloud-800 dark:bg-cloud-900",
        isNight ? "text-lavender-400" : "text-lemon-500"
      )}
      aria-label={isNight ? t("studio.theme.toDay") : t("studio.theme.toNight")}
      aria-pressed={isNight}
    >
      <div
        className={cn(
          "absolute inset-0 rounded-full opacity-50 blur-md transition-colors",
          isNight ? "bg-lavender-400/30" : "bg-lemon-400/30"
        )}
        aria-hidden="true"
      />
      <div className="relative z-10" aria-hidden="true">
        {isNight ? (
          <EmojiIcon emoji="🌙" color="lavender" size="xs" />
        ) : (
          <EmojiIcon emoji="☀️" color="lemon" size="xs" />
        )}
      </div>
    </button>
  );
}
