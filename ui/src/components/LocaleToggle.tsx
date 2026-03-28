import { useI18n } from "../app/locale";

export function LocaleToggle({ className = "" }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();

  return (
    <div
      className={`locale-toggle ${className}`.trim()}
      role="group"
      aria-label={t("locale.switcher")}
    >
      <button
        type="button"
        className={`locale-toggle-btn ${locale === "zh-CN" ? "active" : ""}`}
        onClick={() => setLocale("zh-CN")}
        aria-pressed={locale === "zh-CN"}
      >
        中文
      </button>
      <button
        type="button"
        className={`locale-toggle-btn ${locale === "en-US" ? "active" : ""}`}
        onClick={() => setLocale("en-US")}
        aria-pressed={locale === "en-US"}
      >
        English
      </button>
    </div>
  );
}
