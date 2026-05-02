import { useI18n } from "../app/locale";
import { cn } from "../lib/utils";

export function LocaleToggle({ className = "" }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border border-cloud-200 bg-white p-1 shadow-xs dark:border-cloud-800 dark:bg-cloud-900",
        className
      )}
      role="group"
      aria-label={t("locale.switcher")}
    >
      <button
        type="button"
        className={cn(
          "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
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
          "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
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
