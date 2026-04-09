import { useI18n } from "../app/locale";
import { cn } from "../lib/utils";

export function LocaleToggle({ className = "" }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border border-[var(--glass-border)] bg-[var(--glass-white)] p-1 shadow-xs",
        className
      )}
      role="group"
      aria-label={t("locale.switcher")}
    >
      <button
        type="button"
        className={cn(
          "rounded-full px-2.5 py-1 text-xs font-medium transition-all",
          locale === "zh-CN"
            ? "bg-pink-400 text-white shadow-sm"
            : "text-cloud-600 hover:text-foreground"
        )}
        onClick={() => setLocale("zh-CN")}
        aria-pressed={locale === "zh-CN"}
      >
        中文
      </button>
      <button
        type="button"
        className={cn(
          "rounded-full px-2.5 py-1 text-xs font-medium transition-all",
          locale === "en-US"
            ? "bg-pink-400 text-white shadow-sm"
            : "text-cloud-600 hover:text-foreground"
        )}
        onClick={() => setLocale("en-US")}
        aria-pressed={locale === "en-US"}
      >
        English
      </button>
    </div>
  );
}
