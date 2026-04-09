import { type CSSProperties } from "react";
import { useI18n } from "../../app/locale";
import { EmojiIcon } from "../../components";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { cn } from "../../lib/utils";

export interface GenerationParams {
  resolution: "480p" | "720p" | "1080p";
  duration: "5s" | "10s" | "15s";
  style: "natural" | "vivid" | "anime" | "cinematic";
  quality: "standard" | "high" | "ultra";
}

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  params: GenerationParams;
  onParamsChange: (params: GenerationParams) => void;
}

const resolutionOptions = [
  { value: "480p" as const, label: "480p", width: 854, height: 480, emoji: "📱" },
  { value: "720p" as const, label: "720p HD", width: 1280, height: 720, emoji: "💻" },
  { value: "1080p" as const, label: "1080p FHD", width: 1920, height: 1080, emoji: "🖥️" },
];

const durationOptions = [
  {
    value: "5s" as const,
    labelKey: "studio.settings.duration.5s.label",
    descriptionKey: "studio.settings.duration.5s.description",
    emoji: "⚡",
  },
  {
    value: "10s" as const,
    labelKey: "studio.settings.duration.10s.label",
    descriptionKey: "studio.settings.duration.10s.description",
    emoji: "🎬",
  },
  {
    value: "15s" as const,
    labelKey: "studio.settings.duration.15s.label",
    descriptionKey: "studio.settings.duration.15s.description",
    emoji: "🎭",
  },
];

const styleOptions = [
  {
    value: "natural" as const,
    labelKey: "studio.settings.style.natural",
    color: "var(--color-mint-400)",
    emoji: "🌿",
  },
  {
    value: "vivid" as const,
    labelKey: "studio.settings.style.vivid",
    color: "var(--color-peach-400)",
    emoji: "🌈",
  },
  {
    value: "anime" as const,
    labelKey: "studio.settings.style.anime",
    color: "var(--color-lavender-400)",
    emoji: "🎨",
  },
  {
    value: "cinematic" as const,
    labelKey: "studio.settings.style.cinematic",
    color: "var(--color-sky-400)",
    emoji: "🎬",
  },
];

const qualityOptions = [
  {
    value: "standard" as const,
    labelKey: "studio.settings.quality.standard",
    descriptionKey: "studio.settings.quality.standard.description",
    emoji: "🚀",
  },
  {
    value: "high" as const,
    labelKey: "studio.settings.quality.high",
    descriptionKey: "studio.settings.quality.high.description",
    emoji: "✨",
  },
  {
    value: "ultra" as const,
    labelKey: "studio.settings.quality.ultra",
    descriptionKey: "studio.settings.quality.ultra.description",
    emoji: "💎",
  },
];

export function SettingsPanel({ isOpen, onClose, params, onParamsChange }: SettingsPanelProps) {
  const { t } = useI18n();

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        closeLabel={t("studio.settings.close")}
        closeAutoFocus
        className="max-h-[80vh] overflow-y-auto rounded-3xl border-[var(--glass-border)] bg-[var(--glass-white)] p-0 shadow-2xl backdrop-blur-xl sm:max-w-lg"
      >
        <DialogHeader className="border-b border-[var(--glass-border)] p-5">
          <div className="flex items-center gap-2">
            <EmojiIcon emoji="⚙️" color="mint" size="sm" />
            <DialogTitle className="text-lg font-semibold text-foreground">
              {t("studio.settings.title")}
            </DialogTitle>
          </div>
        </DialogHeader>

        <div className="flex flex-col gap-5 p-5">
          {/* Resolution */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <EmojiIcon emoji="🖥️" color="sky" size="xs" />
              <h3>{t("studio.settings.resolution")}</h3>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {resolutionOptions.map((opt) => {
                const active = params.resolution === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onParamsChange({ ...params, resolution: opt.value })}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-2xl border p-3 text-center transition-all",
                      active
                        ? "border-pink-300 bg-pink-50/60 shadow-sm"
                        : "border-[var(--glass-border)] bg-white/40 hover:-translate-y-0.5 hover:bg-white/70 hover:shadow-sm"
                    )}
                  >
                    <div
                      className={cn(
                        "text-sm font-medium",
                        active ? "text-pink-600" : "text-foreground"
                      )}
                    >
                      {opt.emoji} {opt.label}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {opt.width}×{opt.height}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Duration */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <EmojiIcon emoji="⏱️" color="peach" size="xs" />
              <h3>{t("studio.settings.duration")}</h3>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {durationOptions.map((opt) => {
                const active = params.duration === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onParamsChange({ ...params, duration: opt.value })}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-2xl border p-3 text-center transition-all",
                      active
                        ? "border-pink-300 bg-pink-50/60 shadow-sm"
                        : "border-[var(--glass-border)] bg-white/40 hover:-translate-y-0.5 hover:bg-white/70 hover:shadow-sm"
                    )}
                  >
                    <div
                      className={cn(
                        "text-sm font-medium",
                        active ? "text-pink-600" : "text-foreground"
                      )}
                    >
                      {opt.emoji} {t(opt.labelKey)}
                    </div>
                    <div className="text-xs text-muted-foreground">{t(opt.descriptionKey)}</div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Style */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <EmojiIcon emoji="🎨" color="pink" size="xs" />
              <h3>{t("studio.settings.style")}</h3>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {styleOptions.map((opt) => {
                const active = params.style === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onParamsChange({ ...params, style: opt.value })}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-2xl border p-3 text-center transition-all",
                      active
                        ? "border-pink-300 bg-pink-50/60 shadow-sm"
                        : "border-[var(--glass-border)] bg-white/40 hover:-translate-y-0.5 hover:bg-white/70 hover:shadow-sm"
                    )}
                    style={{ "--style-accent": opt.color } as CSSProperties}
                  >
                    <span className="text-lg">{opt.emoji}</span>
                    <div
                      className={cn(
                        "text-xs font-medium",
                        active ? "text-pink-600" : "text-foreground"
                      )}
                    >
                      {t(opt.labelKey)}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Quality */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <EmojiIcon emoji="💎" color="lavender" size="xs" />
              <h3>{t("studio.settings.quality")}</h3>
            </div>
            <div className="flex flex-col gap-2">
              {qualityOptions.map((opt) => {
                const active = params.quality === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onParamsChange({ ...params, quality: opt.value })}
                    className={cn(
                      "flex items-center justify-between rounded-2xl border p-3 text-left transition-all",
                      active
                        ? "border-pink-300 bg-pink-50/60 shadow-sm"
                        : "border-[var(--glass-border)] bg-white/40 hover:-translate-y-0.5 hover:bg-white/70 hover:shadow-sm"
                    )}
                  >
                    <div className="flex flex-col gap-0.5">
                      <div
                        className={cn(
                          "text-sm font-medium",
                          active ? "text-pink-600" : "text-foreground"
                        )}
                      >
                        {opt.emoji} {t(opt.labelKey)}
                      </div>
                      <div className="text-xs text-muted-foreground">{t(opt.descriptionKey)}</div>
                    </div>
                    {active && (
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-mint-100">
                        <EmojiIcon emoji="✓" color="mint" size="xs" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
